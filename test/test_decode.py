# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

@cocotb.test()
async def test_rom_functionality(dut):
    dut._log.info("Testing rom functionality")
    decode = dut.user_project.u_exu.u_decode

    decode.curr_addr.value = 0
    await Timer(1, units="ns")

    assert decode.micro_op_word == 0x0030 and decode.barrier == 0

STATE_DECODE = 0b00

# Some Helper Functions

async def reset_dut(dut):
    """reset the design and release reset"""
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)

    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)

async def send_macro_op(dut, opcode, fmt=0, u=(0, 0, 0), v=(0, 0, 0)):
    """send a macro op to the decoder (i'll finish when macro op acceptance is finished in RTL)"""
    pass

async def complete_micro_op(dut):
    """signal completion of a micro-operation (i'll do when micro-operation completion handling is implemented)"""
    pass

# 1. FSM (Finite State Machine) Tests

@cocotb.test()
async def test_reset_to_decode(dut):
    """tests that reset places the FSM in the DECODE state."""

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.user_project.u_exu.u_decode

    await reset_dut(dut)
    assert int(decode.state.value) == STATE_DECODE

@cocotb.test()
async def test_decode_to_dispatch(dut):
    """tests that accepting a valid macro op makes decoder DECODE -> DISPATCH"""
    pass

@cocotb.test()
async def test_dispatch_stays_dispatch(dut):
    """tests that the decoder does DISPATCH -> DISPATCH while micro ops aren't finished"""
    pass

@cocotb.test()
async def test_dispatch_to_writeback(dut):
    """tests that completing all required micro-operations makes decoder DISPATCH -> WRITEBACK"""
    pass

@cocotb.test()
async def test_writeback_stays_writeback(dut):
    """tests that the decoder does WRITEBACK -> WRITEBACK while the macro op result has not been accepted"""
    pass

@cocotb.test()
async def test_writeback_to_decode(dut):
    """tests that accepting the macro op result makes decoder WRITEBACK -> DECODE"""
    pass

# 2. Read-Only Memory (ROM) Tests

@cocotb.test()
async def test_scalar_macro_conversion(dut):
    """tests that each scalar macro op is converted into the correct micro op"""
    pass


@cocotb.test()
async def test_vector_rom_ranges(dut):
    """tests that each vector macro op selects the correct ROM range"""
    pass


@cocotb.test()
async def test_rom_contents(dut):
    """tests the complete ROM instruction contents (when all vector sequences are implemented)"""
    pass


@cocotb.test()
async def test_vadd_rom_sequence(dut):
    """tests that the VADD ROM range contains the correct three add micro ops."""
    pass


@cocotb.test()
async def test_rom_default_entry(dut):
    """tests that an unused read-only memory address returns an empty non-barrier micro-operation."""

    decode = dut.user_project.u_exu.u_decode
    await set_rom_addr(decode, 63) # 63 not defined as a rom entry

    assert int(decode.micro_op_word.value) == 0
    assert int(decode.barrier.value) == 0