# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


@cocotb.test()
async def test_project(dut):
    """Smoke test: the wired-up top elaborates, resets, and runs.

    The modules below the top are still stubs, so this only checks the pins
    that the top drives itself. Add checks here as modules are implemented.
    """
    dut._log.info("Start")

    # Set the clock period to 40 ns (25 MHz)
    clock = Clock(dut.clk, 40, units="ns")
    cocotb.start_soon(clock.start())

    # Reset, with the UART receive line (ui_in[3]) idle high
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 0b0000_1000
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1

    dut._log.info("Run")
    await ClockCycles(dut.clk, 100)

    # The bidirectional pins are all inputs
    assert dut.uio_oe.value == 0
