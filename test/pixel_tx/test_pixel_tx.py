# Cocotb tests for pixel_tx (src/io/pixel_tx.sv).
# Run with `make` in this folder. pixel_tx_tb is the toplevel: it flattens the
# colour_if / stream_if ports so we can drive them here.
#
# Each pixel should go out as 00, R, G, B, with 03 in front of any colour byte
# that is 00 or 03. Expected bytes are written out by hand per test.

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, Timer

CLK_PERIOD_NS = 40  # 25 MHz
PIXEL_START = 0x00
DLE = 0x03


def encode_pixel(color):
    """golden reference model, returns the expected byte frame for one 24 bit color"""
    r = (color >> 16) & 0xFF
    g = (color >> 8) & 0xFF
    b = color & 0xFF

    out = [PIXEL_START]                             # frame delimiter, never escaped

    for byte in (r, g, b):
        if byte == PIXEL_START or byte == DLE:      # 0x00 or 0x03, escape it
            out.append(DLE)
        out.append(byte)
    return out


async def reset(dut) -> None:
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, units="ns").start())
    dut.rst_n.value = 0
    dut.pixel_valid.value = 0
    dut.pixel_colour.value = 0
    dut.tx_ready.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)


async def send(dut, pixels: list[int], ready_prob: float = 1.0,
               max_cycles: int = 500) -> list[int]:
    # Offer `pixels` one by one (valid/colour held until the handshake) and
    # collect the bytes pixel_tx sends. Inputs change on the falling edge; a
    # quarter period later we read what the next rising edge will see.
    # tx_ready is high with probability ready_prob each cycle.
    queue = list(pixels)
    sent = []
    for _ in range(max_cycles):
        dut.pixel_valid.value = 1 if queue else 0
        if queue:
            dut.pixel_colour.value = queue[0]
        dut.tx_ready.value = 1 if random.random() < ready_prob else 0

        await Timer(CLK_PERIOD_NS // 4, units="ns")
        if dut.tx_valid.value and dut.tx_ready.value:
            sent.append(int(dut.tx_data.value))
        if dut.pixel_valid.value and dut.pixel_ready.value:
            queue.pop(0)

        await FallingEdge(dut.clk)
        if not queue and not dut.tx_valid.value:
            return sent
    raise AssertionError(f"pixel_tx didn't finish; sent so far: {hexs(sent)}")


def hexs(bs: list[int]) -> str:
    return " ".join(f"{b:02x}" for b in bs)


@cocotb.test()
async def test_escapes(dut):
    """color bytes equal to 0x00 or 0x03 get a DLE in front, start byte and others dont"""
    dut._log.info("start escapes test")

    await reset(dut)

    # color 0x008003, R = 0x00, G = 0x80, B = 0x03, R escaped, G raw, b escaped
    sent = await send(dut, [0x008003])
    expected = [0x00, 0x03, 0x00, 0x80, 0x03, 0x03]             # start, DLE + R, G, DLE + B 

    assert sent == expected, f"tx_byte mismatch: expected [{hexs(expected)}], got [{hexs(sent)}]"

    dut._log.info(f"escaped test ok: {hexs(sent)}")


@cocotb.test()
async def test_01_and_ff_not_escaped(dut):
    """0x01 and 0xFF pass thru raw (only 0x00 and 0x03 are escaped in TX)"""
    dut._log.info("start not escaped test")

    await reset(dut)

    # colour 0x01FF01, R = 0x01, G = 0xFF, B = 0x01, none need escaping
    sent = await send(dut, [0x01FF01])
    expected = [0x00, 0x01, 0xFF, 0x01]                         # start, R G B all raw

    assert sent == expected, f"tx_byte mismatch: expected [{hexs(expected)}], got [{hexs(sent)}]"

    dut._log.info(f"not escaped test ok: {hexs(sent)}")


@cocotb.test()
async def test_b2b(dut):
    """two pixels in a row both frame correctly (second holds until first is fully sent)"""
    dut._log.info("start b2b test")
    
    await reset(dut)

    # p1, 0x112233 = {11, 22, 33} no escapes, p2, 0x030405 = {03, 04, 05} R escaped
    sent = await send(dut, [0x112233, 0x030405])
    expected = [0x00, 0x11, 0x22, 0x33,
                0x00, 0x03, 0x03, 0x04, 0x05]

    assert sent == expected, f"tx_byte mismatch: expected [{hexs(expected)}], got [{hexs(sent)}]"

    dut._log.info(f"b2b test ok, {hexs(sent)}")


@cocotb.test()
async def test_backpressure(dut):
    """random tx_ready (UART busy): no byte dropped, doubled or reordered"""
    dut._log.info("start backpressure test")

    random.seed(1)
    await reset(dut)

    # 3 pixels, 0x030000 = {03, 00, 00} where all are escaped
    sent = await send(dut, [0x008003, 0x123456, 0x030000], ready_prob=0.3)
    expected = [0x00, 0x03, 0x00, 0x80, 0x03, 0x03,
                    0x00, 0x12, 0x34, 0x56,
                    0x00, 0x03, 0x03, 0x03, 0x00, 0x03, 0x00]

    assert sent == expected, f"tx_byte mismatch: expected [{hexs(expected)}], got [{hexs(sent)}]"

    dut._log.info(f"backpressure test ok, {len(sent)} bytes, none lost")


@cocotb.test()
async def test_random_ref(dut):
    """fire many random pixels and check each frame against reference order"""
    dut._log.info("start random reference test")

    random.seed(2)
    await reset(dut)

    for _ in range(200):
        color = random.randint(0, 0xFFFFFF)             # any 24 bit {r,g,b}
        sent = await send(dut, [color])                 # 1 pixel so failure is isolated
        expected = encode_pixel(color)

        assert sent == expected, f"tx_byte mismatch for color {color:#08x}: expected [{hexs(expected)}], got [{hexs(sent)}]"

    dut._log.info("random reference test ok, 200 pixels all matched to model")