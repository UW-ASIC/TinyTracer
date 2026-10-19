import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer, FallingEdge
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
