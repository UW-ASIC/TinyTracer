"""Registered UNSIGNED 16x16 array-core tests for RTL in PR #14.

These do not certify signed fixed-point/FU compliance. See README.md.
"""

import random

import cocotb
from cocotb.triggers import Timer


async def settle():
    await Timer(5, units="ns")


async def initialize(dut):
    dut.clk.value = 0
    dut.rst_n.value = 1
    dut.multiplicand.value = 0
    dut.multiplier_in.value = 0
    await settle()
    dut.rst_n.value = 0
    await settle()
    assert int(dut.product.value) == 0, "asynchronous reset must clear product"
    dut.rst_n.value = 1
    await settle()


async def multiply_cycle(dut, a, b, previous):
    """Change operands off-edge; check hold, capture, and falling-edge hold."""
    dut.clk.value = 0
    dut.multiplicand.value = a
    dut.multiplier_in.value = b
    await settle()
    assert int(dut.product.value) == previous, "product changed before rising edge"
    dut.clk.value = 1
    await settle()
    expected = a * b  # Independent integer oracle; no RTL partial-product logic.
    actual = int(dut.product.value)
    assert actual == expected, (
        f"unsigned {a:#06x} * {b:#06x}: expected {expected:#010x}, "
        f"got {actual:#010x}"
    )
    dut.clk.value = 0
    await settle()
    assert int(dut.product.value) == expected, "product changed on falling edge"
    return expected


@cocotb.test()
async def directed_products(dut):
    """Sign-bit patterns are unsigned here; exercise carry chains and extremes."""
    await initialize(dut)
    values = {0, 1, 2, 3, 0x7FFF, 0x8000, 0x8001, 0xFFFE, 0xFFFF,
              0x5555, 0xAAAA, 0x00FF, 0xFF00, 0x0F0F, 0xF0F0}
    for bit in range(16):
        values.update({1 << bit, (1 << bit) - 1, 0xFFFF ^ (1 << bit)})
    previous = 0
    count = 0
    for a in sorted(values):
        for b in sorted(values):
            previous = await multiply_cycle(dut, a, b, previous)
            count += 1
    dut._log.info("Checked %d directed operand pairs", count)


@cocotb.test()
async def random_back_to_back_products(dut):
    """A reproducible stream accepting fresh operands on every rising edge."""
    await initialize(dut)
    rng = random.Random(0xA51C)
    previous = 0
    for _ in range(5000):
        a, b = rng.getrandbits(16), rng.getrandbits(16)
        previous = await multiply_cycle(dut, a, b, previous)
    dut._log.info("Checked 5000 random pairs, seed 0xA51C")


@cocotb.test()
async def reset_during_activity(dut):
    """Reset clears an existing result without a clock and permits recovery."""
    await initialize(dut)
    previous = 0
    for a, b in [(0xFFFF, 0xFFFF), (0x8000, 3), (17, 23)]:
        previous = await multiply_cycle(dut, a, b, previous)
        dut.rst_n.value = 0
        await settle()
        assert int(dut.product.value) == 0, "reset requires no rising edge"
        # Nonzero inputs and clock transitions must not escape held reset.
        dut.multiplicand.value = 0xFFFF
        dut.multiplier_in.value = 0xFFFF
        dut.clk.value = 1
        await settle()
        assert int(dut.product.value) == 0
        dut.clk.value = 0
        await settle()
        dut.rst_n.value = 1
        await settle()
        assert int(dut.product.value) == 0, "reset release must not capture data"
        previous = 0
    await multiply_cycle(dut, 123, 456, previous)
