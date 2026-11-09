# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

# Cocotb tests for the radix-4 Booth multiplier
# (src/exu/functional_units/booth_mul16.sv), driven through its wrapper
# tt_um_booth_mul16. Run with `make` in this folder.
#
# Wrapper protocol: uio_in = {wr, sel[1:0]}.
#   wr = 1: ui_in is written to byte `sel` of {B_hi, B_lo, A_hi, A_lo}.
#   wr = 0: uo_out shows byte `sel` of the registered 32-bit product.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

CLK_PERIOD_NS = 40  # 25 MHz, same as the chip

# Every A is multiplied by every B and checked against A * B.
A_VALUES = [0, 1, -1, -2, 29, 12345, 21845, -21846, 32767, -32768]
B_VALUES = [0, 1, -1, 94, 32767, -32768, 8738, 18568, -21833, -10901, 24021, 14092]


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
