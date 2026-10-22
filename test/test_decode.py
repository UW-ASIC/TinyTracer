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

async def set_rom_addr(decode, addr):
    """sets the current rom address"""
    decode.curr_addr.value = addr
    await Timer(1, units="ns")

# 1. State Invariant Tests (these ALWAYS need to happen)

@cocotb.test()
async def test_curr_addr_stable_without_micro_accept(dut):
    """tests that curr_addr does not change when no micro op is accepted"""

    dut._log.info("Testing constant address while no micro op accepted...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.user_project.u_exu.u_decode

    await reset_dut(dut)

    decode.curr_addr.value = 5
    await Timer(1, units="ns")

    initial_addr = int(decode.curr_addr.value)

    await ClockCycles(dut.clk, 3)

    assert int(decode.curr_addr.value) == initial_addr


@cocotb.test()
async def test_no_macro_accept_while_busy(dut):
    """tests that the decoder cannot accept a new macro op while in DISPATCH"""

    dut._log.info("Testing no acceptance while in dispatch...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.user_project.u_exu.u_decode

    await reset_dut(dut)

    # manually place decoder in dispatch behavior (still not implemented)
    decode.state.value = 0b01
    await Timer(1, units="ns")

    # make sure we can't accept another value
    assert int(decode.macro.req_ready.value) == 0
    assert int(decode.macro_accept.value) == 0

@cocotb.test()
async def test_inflight_increments_on_issue(dut):
    # tests that the inflight counter actually increases by 1 on a new issue
    pass

@cocotb.test()
async def test_inflight_decrements_on_completion(dut):
    # tests that the inflight counter actually decreases by 1 on a completion
    pass

@cocotb.test()
async def test_inflight_unchanged_on_issue_and_completion(dut):
    # tests that the inflight counter is unchanged on a new issue
    # and completion (+1 -1 = 0)
    pass

@cocotb.test()
async def test_writeback_stable_under_backpressure(dut):
    # tests that the decoder stays in WRITEBACK and keeps the result stable
    # while the next stage is not ready to accept it
    pass

@cocotb.test()
async def test_vector_not_complete_with_inflight_ops(dut):
    # tests that a vector macro op does not finish while there are still
    # unfinished micro ops in flight
    pass

# 2. FSM (Finite State Machine) Tests

@cocotb.test()
async def test_reset_to_decode(dut):
    """tests that reset places the FSM in the DECODE state."""

    dut._log.info("Testing reset sets the FSM to decode...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.user_project.u_exu.u_decode

    await reset_dut(dut)

    assert int(decode.state.value) == STATE_DECODE


@cocotb.test()
async def test_decode_to_dispatch(dut):
    """tests that accepting a valid macro op makes decoder DECODE -> DISPATCH"""

    dut._log.info("Testing decode to dispatch...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.user_project.u_exu.u_decode

    await reset_dut(dut)

    # send a valid scalar macro op (note that M_ADD = 0 for the op code)
    decode.macro.req_valid.value = 1
    decode.macro.req_op.op.value = 0b00000

    await Timer(1, units="ns")

    # decoder should be ready to accept in DECODE
    assert int(decode.macro.req_ready.value) == 1
    assert int(decode.macro_accept.value) == 1

    # acceptance happens on the next clock edge
    await ClockCycles(dut.clk, 1)

    assert int(decode.state.value) == 0b01

    decode.macro.req_valid.value = 0


@cocotb.test()
async def test_dispatch_stays_dispatch(dut):
    """tests that the decoder does DISPATCH -> DISPATCH while micro ops aren't finished"""

    dut._log.info("Testing dispatch stays dispatch...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.user_project.u_exu.u_decode

    await reset_dut(dut)

    # enter DISPATCH through a real macro-op acceptance
    decode.macro.req_valid.value = 1
    decode.macro.req_op.op.value = 0b00000 # 

    await ClockCycles(dut.clk, 1)

    decode.macro.req_valid.value = 0

    assert int(decode.state.value) == 0b01

    # DISPATCH currently has no completion logic,
    # so it should remain in DISPATCH
    await ClockCycles(dut.clk, 3)

    assert int(decode.state.value) == 0b01

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

# 3. Read-Only Memory (ROM) Tests

@cocotb.test()
async def test_scalar_macro_conversion(dut):
    """tests that each scalar macro op is converted into the correct micro op"""

    dut._log.info("Testing scalar macro conversion...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.user_project.u_exu.u_decode

    await reset_dut(dut)

    # scalar macro ops M_ADD through M_MAG
    scalar_ops = [
        0b00000, # ADD
        0b00001, # SUB
        0b00010, # EQ
        0b00011, # NE
        0b00100, # LT
        0b00101, # GE
        0b00110, # MUL
        0b00111, # DIV
        0b01000, # SQRT
        0b01001, # COS
        0b01011  # MAG
    ]

    # test each scalar macro operation
    for opcode in scalar_ops:
        decode.macro.req_valid.value = 1
        decode.macro.req_op.op.value = opcode
        decode.macro.req_op.u.x.value = 0x1234
        decode.macro.req_op.v.x.value = 0x5678

        await Timer(1, units="ns")

        # scalar macro opcode becomes the lower 4-bit micro opcode
        assert int(decode.micro.req_valid.value) == 1
        assert int(decode.micro.req_direct.value) == 1
        assert int(decode.micro.req_u1.value) == 0x1234
        assert int(decode.micro.req_v1.value) == 0x5678

        # RD, RS1 and RS2 should all be 0 for direct scalar operations
        expected_micro_word = opcode & 0xF
        assert int(decode.micro.req_op.value) == expected_micro_word

    decode.macro.req_valid.value = 0


@cocotb.test()
async def test_vector_rom_ranges(dut):
    """tests that each vector macro op selects the correct ROM range"""

    dut._log.info("Testing vector ROM ranges...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.user_project.u_exu.u_decode

    await reset_dut(dut)

    # all macro ops and their corresponding ranges
    vector_ranges = [
        (0b01100, 0, 3),   # VADD
        (0b01101, 3, 6),   # VSUB
        (0b01110, 6, 9),   # SCAL_VEC
        (0b01111, 9, 14),  # DOT
        (0b10000, 14, 23), # CROSS
        (0b10001, 23, 29), # NORM
        (0b10010, 29, 32), # SPHERE_NORM
        (0b10011, 32, 35)  # VMUL
    ]

    for opcode, start_addr, end_addr in vector_ranges:
        decode.macro.req_valid.value = 1
        decode.macro.req_op.op.value = opcode

        await Timer(1, units="ns")

        # accept the vector macro op
        await ClockCycles(dut.clk, 1)

        assert int(decode.curr_addr.value) == start_addr
        assert int(decode.op_addr_end.value) == end_addr

        # reset before testing the next macro op
        decode.macro.req_valid.value = 0
        await reset_dut(dut)


@cocotb.test()
async def test_rom_contents(dut):
    """tests the complete ROM instruction contents (when all vector sequences are implemented)"""
    pass


@cocotb.test()
async def test_vadd_rom_sequence(dut):
    """tests that the VADD ROM range contains the correct three add micro ops."""

    dut._log.info("Testing VADD ROM sequence...")

    # i'll make more once the other RTL is developed...

    decode = dut.user_project.u_exu.u_decode

    expected = [
        (0, 0x0030, 0),
        (1, 0x04C0, 0),
        (2, 0x0950, 0)
    ]

    for addr, micro_op, barrier in expected:
        await set_rom_addr(decode, addr)

        assert int(decode.micro_op_word.value) == micro_op
        assert int(decode.barrier.value) == barrier


@cocotb.test()
async def test_rom_default_entry(dut):
    """tests that an unused read-only memory address returns an empty non-barrier micro-operation."""

    dut._log.info("Testing unused ROM entry...")

    decode = dut.user_project.u_exu.u_decode

    # read only
    await set_rom_addr(decode, 63)

    assert int(decode.micro_op_word.value) == 0
    assert int(decode.barrier.value) == 0