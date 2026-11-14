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
    # Example from the plan: (00, 80, 03) -> 00 03 00 80 03 03
    await reset(dut)
    sent = await send(dut, [0x008003])
    assert sent == [0x00, 0x03, 0x00, 0x80, 0x03, 0x03], hexs(sent)


@cocotb.test()
async def test_01_and_ff_not_escaped(dut):
    await reset(dut)
    sent = await send(dut, [0x01FF01])
    assert sent == [0x00, 0x01, 0xFF, 0x01], hexs(sent)


@cocotb.test()
async def test_back_to_back(dut):
    # Second pixel waits (ready low) until the first is fully sent.
    await reset(dut)
    sent = await send(dut, [0x112233, 0x030405])
    assert sent == [0x00, 0x11, 0x22, 0x33,
                    0x00, 0x03, 0x03, 0x04, 0x05], hexs(sent)


@cocotb.test()
async def test_backpressure(dut):
    # The real UART holds ready low for ~2000 clk per byte. With ready
    # randomly low, no byte may be dropped, doubled or reordered.
    random.seed(1)
    await reset(dut)
    sent = await send(dut, [0x008003, 0x123456, 0x030000], ready_prob=0.3)
    assert sent == [0x00, 0x03, 0x00, 0x80, 0x03, 0x03,
                    0x00, 0x12, 0x34, 0x56,
                    0x00, 0x03, 0x03, 0x03, 0x00, 0x03, 0x00], hexs(sent)
