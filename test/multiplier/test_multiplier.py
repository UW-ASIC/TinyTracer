"""Tests the unsigned 16x16 array core in PR #14.
Signed fixed-point scaling and FU handshakes are not covered here.
"""

import random

import cocotb
from cocotb.triggers import Timer


async def settle():
    await Timer(5, units="ns")


async def setup(dut):
    dut.clk.value = 0
    dut.rst_n.value = 1
    dut.multiplicand.value = 0
    dut.multiplier_in.value = 0
    await settle()

    dut.rst_n.value = 0
    await settle()
    assert int(dut.product.value) == 0, "Reset did not clear product"

    dut.rst_n.value = 1
    await settle()


async def check_product(dut, a, b, previous):
    # Change inputs while the clock is low.
    dut.clk.value = 0
    dut.multiplicand.value = a
    dut.multiplier_in.value = b
    await settle()

    # Output must retain the previous result until the rising edge.
    assert int(dut.product.value) == previous, (
        "Product changed before the rising edge"
    )

    dut.clk.value = 1
    await settle()

    expected = a * b
    actual = int(dut.product.value)

    assert actual == expected, (
        f"{a:#06x} * {b:#06x}: "
        f"expected {expected:#010x}, got {actual:#010x}"
    )

    dut.clk.value = 0
    await settle()

    assert int(dut.product.value) == expected, (
        "Product changed on the falling edge"
    )

    return expected


@cocotb.test()
async def test_directed_products(dut):
    await setup(dut)

    values = {
        0, 1, 2, 3,
        0x7FFF, 0x8000, 0x8001, 0xFFFE, 0xFFFF,
        0x5555, 0xAAAA, 0x00FF, 0xFF00, 0x0F0F, 0xF0F0,
    }

    # Add single-bit patterns and patterns containing runs of ones.
    for bit in range(16):
        values.add(1 << bit)
        values.add((1 << bit) - 1)
        values.add(0xFFFF ^ (1 << bit))

    previous = 0

    for a in sorted(values):
        for b in sorted(values):
            previous = await check_product(dut, a, b, previous)


@cocotb.test()
async def test_random_products(dut):
    await setup(dut)

    rng = random.Random(0xA51C)
    previous = 0

    for _ in range(5000):
        a = rng.getrandbits(16)
        b = rng.getrandbits(16)
        previous = await check_product(dut, a, b, previous)


@cocotb.test()
async def test_reset_during_activity(dut):
    await setup(dut)

    previous = 0

    for a, b in [(0xFFFF, 0xFFFF), (0x8000, 3), (17, 23)]:
        previous = await check_product(dut, a, b, previous)

        # Asynchronous reset must clear output without a clock edge.
        dut.rst_n.value = 0
        await settle()
        assert int(dut.product.value) == 0

        # Output must stay zero even with nonzero inputs and a clock edge.
        dut.multiplicand.value = 0xFFFF
        dut.multiplier_in.value = 0xFFFF
        dut.clk.value = 1
        await settle()
        assert int(dut.product.value) == 0

        dut.clk.value = 0
        await settle()

        # Releasing reset must not capture inputs until the next edge.
        dut.rst_n.value = 1
        await settle()
        assert int(dut.product.value) == 0

        previous = 0

    # Check normal operation resumes after reset.
    await check_product(dut, 123, 456, previous)