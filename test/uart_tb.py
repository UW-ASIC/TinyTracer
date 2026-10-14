import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer
 
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