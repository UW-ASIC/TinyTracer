import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, FallingEdge, Timer, FallingEdge
from cocotb.utils import get_sim_time

CLK_NS = 40
CLKQ_DIV = 8
BIT_CYCLES = 16 * CLKQ_DIV
BIT_NS = BIT_CYCLES * CLK_NS
FRAME_CYCLES = 10 * BIT_CYCLES

EDGE_PATTERNS = [0x00, 0xFF, 0x55, 0xAA, 0x01, 0x80, 0x0F, 0xF0]


async def make_clkq(dut):
    while True:
        dut.clkq.value = 0
        await ClockCycles(dut.clk, CLKQ_DIV // 2)
        dut.clkq.value = 1
        await ClockCycles(dut.clk, CLKQ_DIV // 2)


async def setup(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_NS, "ns").start())
    cocotb.start_soon(make_clkq(dut))
    dut.TT_RX.value = 1
    dut.rx_ready.value = 1
    dut.tx_valid.value = 0
    dut.tx_data.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, BIT_CYCLES)

# rx helper functions
async def send_byte(dut, byte, stop_bit=1):
    bits = [0] + [(byte >> i) & 1 for i in range(8)] + [stop_bit]
    for bit in bits:
        dut.TT_RX.value = bit
        await Timer(BIT_NS, "ns")
    dut.TT_RX.value = 1


async def collect_bytes(dut, received):
    while True:
        await RisingEdge(dut.clk)
        if dut.rx_valid.value == 1 and dut.rx_ready.value == 1:
            received.append(int(dut.rx_data.value))


# tx helper functions
async def submit_tx_byte(dut, byte):
    await FallingEdge(dut.clk)
    dut.tx_data.value = byte
    dut.tx_valid.value = 1

    while True:
        await RisingEdge(dut.clk)
        if dut.tx_ready.value == 1:
            break

    await FallingEdge(dut.clk)
    dut.tx_valid.value = 0

async def check_tx_bytes(dut, data):
    for byte in data:
        await FallingEdge(dut.TT_TX)

        for i in range(6):
            await Timer(BIT_NS // 8, "ns")
            assert dut.TT_TX.value == 0, "TX start bit isn't low"

        for i in range(8):
            if i == 0:
                wait_ns = 3 * BIT_NS // 4
            else:
                wait_ns = BIT_NS
            await Timer(wait_ns, "ns")
            expected = (byte >> i) & 1

            assert dut.TT_TX.value == expected, f"Wrong TX bit {i}: expected {expected}, got {dut.TT_TX.value}"
            assert dut.tx_ready.value == 0, "TX became ready during transmission"
            
        await Timer(BIT_NS, "ns")
        assert dut.TT_TX.value == 1, "TX stop bit isn't high"
        assert dut.tx_ready.value == 0, "TX became ready during stop bit"


# rx testing
@cocotb.test()
async def test_rx_reset_and_idle(dut):
    await setup(dut)
    assert dut.rx_valid.value == 0
    for _ in range(3 * FRAME_CYCLES):
        await RisingEdge(dut.clk)
        assert dut.rx_valid.value == 0


@cocotb.test()
async def test_rx_bit_patterns(dut):
    await setup(dut)
    got = []
    cocotb.start_soon(collect_bytes(dut, got))
    for b in EDGE_PATTERNS:
        await send_byte(dut, b)
        await ClockCycles(dut.clk, 2 * BIT_CYCLES)
    assert got == EDGE_PATTERNS, f"sent {EDGE_PATTERNS}, got {got}"


@cocotb.test()
async def test_rx_back_to_back(dut):
    await setup(dut)
    got = []
    cocotb.start_soon(collect_bytes(dut, got))
    data = [random.randrange(256) for _ in range(32)]
    for b in data:
        await send_byte(dut, b)
    await ClockCycles(dut.clk, FRAME_CYCLES)
    assert got == data, f"sent {data}, got {got}"


@cocotb.test()
async def test_rx_stop(dut):
    await setup(dut)
    got = []
    cocotb.start_soon(collect_bytes(dut, got))
    await send_byte(dut, 0xA5, stop_bit=0)
    await ClockCycles(dut.clk, FRAME_CYCLES)
    assert got == [], f"bad frame not dropped: {got}"
    await send_byte(dut, 0x3C)
    await ClockCycles(dut.clk, FRAME_CYCLES)
    assert got == [0x3C], f"good byte after bad one failed: {got}"


@cocotb.test()
async def test_rx_false_start(dut):
    await setup(dut)
    got = []
    cocotb.start_soon(collect_bytes(dut, got))
    dut.TT_RX.value = 0
    await ClockCycles(dut.clk, 3 * CLKQ_DIV)
    dut.TT_RX.value = 1
    await ClockCycles(dut.clk, 2 * FRAME_CYCLES)
    assert got == [], f"glitch produced a byte: {got}"
    await send_byte(dut, 0x96)
    await ClockCycles(dut.clk, FRAME_CYCLES)
    assert got == [0x96], f"good byte after glitch failed: {got}"

# tx testing
@cocotb.test()
async def test_tx_idle_and_busy(dut):
    await setup(dut)
    assert dut.TT_TX.value == 1, f"TX isn't idling high: got {dut.TT_TX.value}"
    assert dut.tx_ready.value == 1, f"TX isn't ready after reset: got {dut.tx_ready.value}"
    await FallingEdge(dut.clk)
    dut.tx_data.value = 0xA5
    dut.tx_valid.value = 1

    await RisingEdge(dut.clk) 

    await FallingEdge(dut.clk)
    dut.tx_valid.value = 0
    assert dut.tx_ready.value == 0, "TX didn't become busy"

@cocotb.test()
async def test_tx_back_to_back(dut):
    await setup(dut)

    data = [random.randrange(256) for _ in range(32)]
    checker = cocotb.start_soon(check_tx_bytes(dut, data))

    for byte in data:
        await submit_tx_byte(dut, byte)

    await checker
    await ClockCycles(dut.clk, BIT_CYCLES)

    assert dut.tx_ready.value == 1, "TX didn't become ready again"

@cocotb.test()
async def test_tx_bit_patterns(dut):
    await setup(dut)

    for byte in EDGE_PATTERNS:
        checker = cocotb.start_soon(check_tx_bytes(dut, [byte]))
        await submit_tx_byte(dut, byte)

        assert dut.tx_ready.value == 0, "TX didn't become busy"

        await checker
        await ClockCycles(dut.clk, BIT_CYCLES)

        assert dut.tx_ready.value == 1, "TX didn't become ready again"

@cocotb.test()
async def test_tx_bit_timing(dut):
    await setup(dut)

    sender = cocotb.start_soon(submit_tx_byte(dut, 0x55))

    await FallingEdge(dut.TT_TX)
    start_time = get_sim_time(units="ns")
    await RisingEdge(dut.TT_TX)
    previous_time = get_sim_time(units="ns")

    # test start bit 
    start_duration = previous_time - start_time
    minimum = BIT_NS - CLKQ_DIV * CLK_NS
    maximum = BIT_NS + 3 * CLK_NS
    assert minimum <= start_duration <= maximum, (
        f"Start bit lasted {start_duration} ns; expected between {minimum} and {maximum} ns")

    # test bits d0 to d7
    for i in range(8):
        if i % 2 == 0:
            await FallingEdge(dut.TT_TX)
        else:
            await RisingEdge(dut.TT_TX)
        current_time = get_sim_time(units="ns")
        duration = current_time - previous_time

        assert abs(duration - BIT_NS) < 1, (f"Data bit {i} lasted {duration} ns; expected {BIT_NS} ns")
        previous_time = current_time

    # test stop bit
    await RisingEdge(dut.tx_ready)
    duration = get_sim_time(units="ns") - previous_time

    assert abs(duration - BIT_NS) < 1, (f"Stop bit lasted {duration} ns; expected {BIT_NS} ns")
    await sender


@cocotb.test()
async def test_rx_start_phase(dut):
    """Checking that bytes arrive correctly at different start times relative to clkq - so receiving works even if host/chip clocks aren't aligned"""
    await setup(dut)
    got = []
    expected = []
    cocotb.start_soon(collect_bytes(dut, got))

    sample_ns = CLKQ_DIV * CLK_NS
    # sweep start timing across one clkq period
    for phase_ns in range(1, sample_ns, CLK_NS // 2):
        # offset the start from a sampling edge
        await RisingEdge(dut.clkq)
        await Timer(phase_ns, "ns")
        # cycle through the edge patterns
        byte = EDGE_PATTERNS[len(expected) % len(EDGE_PATTERNS)]
        await send_byte(dut, byte)
        await ClockCycles(dut.clk, 2 * BIT_CYCLES)
        expected.append(byte)
        # check for missing or extra bytes
        assert got == expected, f"start offset {phase_ns} ns: expected {expected}, got {got}"


@cocotb.test()
async def test_rx_bit_jitter(dut):
    """Checking that bytes decode correctly when individual bits are shorter or longer."""
    await setup(dut)
    got = []
    expected = []
    cocotb.start_soon(collect_bytes(dut, got))

    # short and long bits cancel out
    jitter_ticks = [1, -1, 2, -2, -1, 1, -2, 2, 0, 0]
    for byte in EDGE_PATTERNS:
        # frame the byte starting with lsb
        bits = [0] + [(byte >> i) & 1 for i in range(8)] + [1]
        for bit, jitter in zip(bits, jitter_ticks):
            dut.TT_RX.value = bit
            # vary each bit by up to two clkq ticks
            await Timer(BIT_NS + jitter * CLKQ_DIV * CLK_NS, "ns")
        dut.TT_RX.value = 1
        await ClockCycles(dut.clk, 2 * BIT_CYCLES)
        expected.append(byte)
        # jitter must not change the decoded byte
        assert got == expected, f"jittered byte {byte:#04x}: expected {expected}, got {got}"


@cocotb.test()
async def test_rx_baud_mismatch(dut):
    """Send entire frames with bit lengths 2% shorter or longer. Checks the difference between host/chip baud rate can be tolerated."""
    await setup(dut)
    got = []
    expected = []
    cocotb.start_soon(collect_bytes(dut, got))

    # try bit periods 2% shorter and longer
    for period_ns in (BIT_NS - BIT_NS // 50, BIT_NS + BIT_NS // 50):
        for byte in EDGE_PATTERNS:
            # frame the byte with lsb first
            bits = [0] + [(byte >> i) & 1 for i in range(8)] + [1]
            for bit in bits:
                dut.TT_RX.value = bit
                # hold period for full frame
                await Timer(period_ns, "ns")
            dut.TT_RX.value = 1
            await ClockCycles(dut.clk, 2 * BIT_CYCLES)
            expected.append(byte)
            # check decoding despite accumulated timing drift
            assert got == expected, (
                f"bit period {period_ns} ns, byte {byte:#04x}: expected {expected}, got {got}"
            )


@cocotb.test()
async def test_rx_single_sample_noise(dut):
    """Check that one wrong sample per bit does not corrupt the received byte by flipping one of the 3 values and ensuring the other 2 outvote the noise."""
    await setup(dut)
    got = []
    expected = []
    cocotb.start_soon(collect_bytes(dut, got))

    # corrupt each voting position in turn
    for noisy_sample in (6, 8, 10):
        for byte in (0x00, 0xFF, 0x55, 0xAA):
            # leave time for CDC settling before sample 0
            await FallingEdge(dut.clkq)
            bits = [0] + [(byte >> i) & 1 for i in range(8)] + [1]
            for bit in bits:
                for sample in range(16):
                    # flip one sample in every frame bit
                    dut.TT_RX.value = bit ^ int(sample == noisy_sample)
                    # set up the next sample on a falling edge
                    await FallingEdge(dut.clkq)
            dut.TT_RX.value = 1
            await ClockCycles(dut.clk, 2 * BIT_CYCLES)
            expected.append(byte)
            # the other two votes should preserve the correct byte
            assert got == expected, (
                f"noise at sample {noisy_sample}, byte {byte:#04x}: "
                f"expected {expected}, got {got}"
            )


@cocotb.test()
async def test_rx_two_sample_majority(dut):
    """
    Check that any two correct votes among samples 6, 8, and 10 win.
    
    Tries every pair among 6,8,10 making only 2 of those 3 positions set to the "expected" value.
    It's not meant to be a realistic scenario (if all 14 bits were the opposite, we would probably want the other value), but confirms that the correct samples determine the result.
    """
    await setup(dut)
    got = []
    expected = []
    cocotb.start_soon(collect_bytes(dut, got))

    # try every pair of correct votes
    for correct_samples in ((6, 8), (6, 10), (8, 10)):
        for byte in (0x00, 0xFF, 0x55, 0xAA):
            await FallingEdge(dut.clkq)
            dut.TT_RX.value = 0
            # count start edges to avoid a timer/edge race
            for _ in range(16):
                await FallingEdge(dut.clkq)
            for bit_index in range(8):
                bit = (byte >> bit_index) & 1
                for sample in range(16):
                    # invert every sample outside the selected pair
                    dut.TT_RX.value = bit if sample in correct_samples else bit ^ 1
                    await FallingEdge(dut.clkq)
            # finish with a clean stop bit
            dut.TT_RX.value = 1
            await Timer(BIT_NS, "ns")
            await ClockCycles(dut.clk, 2 * BIT_CYCLES)
            expected.append(byte)
            # two correct votes must determine the byte
            assert got == expected, (
                f"correct samples {correct_samples}, byte {byte:#04x}: "
                f"expected {expected}, got {got}"
            )
