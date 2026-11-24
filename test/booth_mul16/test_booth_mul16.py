# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

# Cocotb tests for the radix-4 Booth multiplier
# (src/exu/functional_units/booth_mul16.sv), driven through its wrapper
# tt_um_booth_mul16. Run with `make` in this folder.
#
# Wrapper protocol: uio_in = {wr, sel[1:0]}.
#   wr = 1: ui_in is written to byte `sel` of {B_hi, B_lo, A_hi, A_lo}.
#   wr = 0: uo_out shows byte `sel` of the registered 32-bit product.

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

CLK_PERIOD_NS = 40  # 25 MHz, same as the chip

# 200 values of A and 200 of B; every A is multiplied by every B, 40,000 in all.
N_VALUES = 200


def s16(x):
    """16-bit pattern -> signed value."""
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x


# Values that tend to break multipliers. A and B both start with these, so
# every corner case is also multiplied by every other one.
CORNER_VALUES = (
    [0, 1, -1, 2, -2, 3, -3, 29, 94, 12345, -12345]
    # Ends of the range and their neighbours
    + [32767, -32768, 32766, -32767]
    # Powers of two, one less, and their negatives
    + [v for k in range(15) for v in (1 << k, (1 << k) - 1, -(1 << k), 1 - (1 << k))]
    # Bit patterns, as B they give fixed Booth digit sequences, row 0 first:
    #   0x5555 all +1; 0xAAAA -2 then all -1; 0x3333 -1, +1, -1, ...;
    #   0x6DB6 -2, +2, -1, -1, +2, ...; 0x9249 +1, -2, +1, +1, -2, ...
    # The random values below cover every window in every row as well.
    + [s16(x) for x in (0x5555, 0xAAAA, 0x3333, 0xCCCC, 0x0F0F, 0xF0F0,
                        0x00FF, 0xFF00, 0x6DB6, 0x9249, 0x8001, 0x7FFE)]
)


def make_values(seed):
    """N_VALUES distinct signed 16-bit values: CORNER_VALUES, then random ones.

    A fixed seed gives the same list every run, so a failure can be rerun.
    """
    values = list(dict.fromkeys(CORNER_VALUES))  # drop repeats, keep order
    assert len(values) <= N_VALUES
    rng = random.Random(seed)
    seen = set(values)
    while len(values) < N_VALUES:
        v = rng.randint(-32768, 32767)
        if v not in seen:
            seen.add(v)
            values.append(v)
    return values


A_VALUES = make_values(seed=1)
B_VALUES = make_values(seed=2)


@cocotb.test()
async def test_multiply(dut):
    # `units` and int(value) work on both cocotb 1.9 (requirements.txt) and 2.x
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, units="ns").start())

    # Reset
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1

    for a in A_VALUES:
        for b in B_VALUES:
            # Write A low, A high, B low, B high: ui_in = byte, uio_in = {wr=1, sel}
            for sel, byte in enumerate([a & 0xFF, (a >> 8) & 0xFF, b & 0xFF, (b >> 8) & 0xFF]):
                dut.ui_in.value = byte
                dut.uio_in.value = 0b100 | sel
                await ClockCycles(dut.clk, 1)

            # One clock with wr = 0: the product register captures A * B
            dut.uio_in.value = 0
            await ClockCycles(dut.clk, 1)

            # Read the product a byte at a time, sel = 0..3
            p = 0
            for sel in range(4):
                dut.uio_in.value = sel
                await ClockCycles(dut.clk, 1)
                p |= int(dut.uo_out.value) << (8 * sel)
            if p >= 2**31:
                p -= 2**32  # 32-bit two's complement to signed

            assert p == a * b, f"{a} * {b}: got {p}, expected {a * b}"

    dut._log.info(f"{len(A_VALUES)} x {len(B_VALUES)} = "
                  f"{len(A_VALUES) * len(B_VALUES)} products checked")
