# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer, RisingEdge, ReadOnly

@cocotb.test()
async def test_rom_functionality(dut):
    dut._log.info("Testing rom functionality")
    decode = dut.dut

    decode.curr_addr.value = 0
    await Timer(1, units="ns")

    assert decode.micro_op_word == 0x0030 and decode.barrier == 0

STATE_DECODE = 0b00

# Some Helper Functions

async def reset_dut(dut):
    """reset the design and release reset"""

    # no handshakes while leaving reset
    dut.macro_req_valid.value = 0
    dut.macro_resp_ready.value = 0
    dut.micro_req_ready.value = 0
    dut.micro_resp_done.value = 0

    dut.macro_opcode.value = 0
    dut.macro_fmt.value = 0
    dut.macro_u_x.value = 0
    dut.macro_v_x.value = 0

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)

    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)

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
    decode = dut.dut

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
    decode = dut.dut

    await reset_dut(dut)

    # (VADD) enter DISPATCH
    dut.macro_req_valid.value = 1
    dut.macro_opcode.value = 0b01100

    # don't allow micro ops to issue
    dut.micro_req_ready.value = 0

    await Timer(1, units="ns")
    assert int(dut.macro_req_ready.value) == 1

    await RisingEdge(dut.clk)
    await ReadOnly()

    assert int(decode.state.value) == 0b01

    # while busy, decoder must not accept another macro op
    assert int(dut.macro_req_ready.value) == 0
    assert int(decode.macro_accept.value) == 0

@cocotb.test()
async def test_inflight_increments_on_issue(dut):
    """tests that inflight increments when a micro op is issued"""

    dut._log.info("Testing inflight increments on micro issue...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)

    # send VADD so decoder enters DISPATCH with ROM work to issue
    dut.macro_opcode.value = 0b01100
    dut.macro_req_valid.value = 1

    # initially prevent micro-op issue
    dut.micro_req_ready.value = 0

    await Timer(1, units="ns")
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    # now we're in DISPATCH, with nothing inflight yet
    assert int(decode.state.value) == 0b01
    assert int(decode.inflight.value) == 0

    # allow the first micro-op to be accepted
    dut.micro_req_ready.value = 1

    await Timer(1, units="ns")

    # handshake should now be active (this is not the actual test)
    assert int(dut.micro_req_valid.value) == 1
    assert int(decode.micro_issue.value) == 1

    # issue is counted on the next rising edge
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.inflight.value) == 1

@cocotb.test()
async def test_inflight_decrements_on_completion(dut):
    """tests that inflight decrements when a micro op completes"""

    dut._log.info("Testing inflight decrements on micro completion...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)

    # enter DISPATCH with VADD
    dut.macro_opcode.value = 0b01100
    dut.macro_req_valid.value = 1
    dut.micro_req_ready.value = 0

    await Timer(1, units="ns")
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01

    # issue one micro op so inflight becomes 1
    dut.micro_req_ready.value = 1

    await Timer(1, units="ns")
    assert int(decode.micro_issue.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.inflight.value) == 1

    # stop issuing new micro ops
    dut.micro_req_ready.value = 0

    # signal completion of the outstanding micro op
    dut.micro_resp_done.value = 1

    await Timer(1, units="ns")

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.inflight.value) == 0

@cocotb.test()
async def test_inflight_unchanged_on_issue_and_completion(dut):
    """tests that inflight stays unchanged when one op issues and one completes"""

    dut._log.info("Testing simultaneous micro issue and completion...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)

    # enter DISPATCH with VADD
    dut.macro_opcode.value = 0b01100
    dut.macro_req_valid.value = 1
    dut.micro_req_ready.value = 0

    await Timer(1, units="ns")
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    # first issue one op so inflight becomes 1
    dut.micro_req_ready.value = 1

    await Timer(1, units="ns")
    assert int(decode.micro_issue.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.inflight.value) == 1

    # next cycle: one new issue + one completion
    dut.micro_req_ready.value = 1
    dut.micro_resp_done.value = 1

    await Timer(1, units="ns")

    assert int(decode.micro_issue.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    # +1 and -1 cancel
    assert int(decode.inflight.value) == 1

@cocotb.test()
async def test_writeback_stable_under_backpressure(dut):
    """tests that WRITEBACK remains stable while the macro result is not accepted"""

    dut._log.info("Testing writeback stability under backpressure...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)

    # don't allow the macro result to be accepted
    dut.macro_resp_ready.value = 0

    # send scalar ADD
    dut.macro_opcode.value = 0b00000
    dut.macro_req_valid.value = 1

    await Timer(1, units="ns")
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    # should now be in DISPATCH
    assert int(decode.state.value) == 0b01

    # signal that the scalar micro op completed
    dut.micro_resp_done.value = 1

    await Timer(1, units="ns")
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    # should now be in WRITEBACK
    assert int(decode.state.value) == 0b10
    assert int(dut.macro_resp_valid.value) == 1

    # remove completion signal
    dut.micro_resp_done.value = 0

    # receiver still isn't ready
    dut.macro_resp_ready.value = 0

    # WRITEBACK should remain stable
    await ClockCycles(dut.clk, 3)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b10
    assert int(dut.macro_resp_valid.value) == 1

@cocotb.test()
async def test_vector_not_complete_with_inflight_ops(dut):
    """tests that a vector macro does not complete while micro ops are still inflight"""

    dut._log.info("Testing vector does not complete with inflight ops...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)

    # enter DISPATCH with VADD
    dut.macro_opcode.value = 0b01100
    dut.macro_req_valid.value = 1
    dut.micro_req_ready.value = 0

    await Timer(1, units="ns")
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01

    # issue one micro op so inflight becomes 1
    dut.micro_req_ready.value = 1

    await Timer(1, units="ns")
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.inflight.value) == 1

    # prevent more issues
    dut.micro_req_ready.value = 0

    # move to end of vector ROM range
    decode.curr_addr.value = int(decode.op_addr_end.value)

    await Timer(1, units="ns")

    # end address reached, but outstanding work remains
    assert int(decode.inflight.value) == 1
    assert int(decode.vector_done.value) == 0

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    # must remain in DISPATCH
    assert int(decode.state.value) == 0b01

# 2. FSM (Finite State Machine) Tests

@cocotb.test()
async def test_reset_to_decode(dut):
    """tests that reset places the FSM in the DECODE state."""

    dut._log.info("Testing reset sets the FSM to decode...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)

    assert int(decode.state.value) == STATE_DECODE


@cocotb.test()
async def test_decode_to_dispatch(dut):
    """tests that accepting a valid macro op makes decoder DECODE -> DISPATCH"""

    dut._log.info("Testing decode to dispatch...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)

    # send scalar M_ADD
    dut.macro_req_valid.value = 1
    dut.macro_opcode.value = 0b00000

    await Timer(1, units="ns")

    assert int(dut.macro_req_ready.value) == 1
    assert int(decode.macro_accept.value) == 1

    # wait for acceptance edge, then let sequential logic settle
    await RisingEdge(dut.clk)
    await ReadOnly()

    assert int(decode.state.value) == 0b01


@cocotb.test()
async def test_dispatch_stays_dispatch(dut):
    """tests that the decoder does DISPATCH -> DISPATCH while micro ops aren't finished"""

    dut._log.info("Testing dispatch stays dispatch...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)

    dut.micro_req_ready.value = 0
    dut.macro_req_valid.value = 1
    dut.macro_opcode.value = 0b01100  # VADD

    await Timer(1, units="ns")
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01

    # macro interface stays asserted, but it cannot be accepted in DISPATCH
    await ClockCycles(dut.clk, 3)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01

@cocotb.test()
async def test_dispatch_to_writeback(dut):
    """tests that completed vector work makes decoder DISPATCH -> WRITEBACK"""

    dut._log.info("Testing dispatch to writeback...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)

    # enter DISPATCH with VADD
    dut.macro_opcode.value = 0b01100
    dut.macro_req_valid.value = 1
    dut.micro_req_ready.value = 0

    await Timer(1, units="ns")
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01

    # simulate being at the end of the vector sequence
    decode.curr_addr.value = int(decode.op_addr_end.value)

    # no outstanding micro ops
    assert int(decode.inflight.value) == 0

    await Timer(1, units="ns")

    # completion condition should now be true
    assert int(decode.vector_done.value) == 1

    # FSM should transition on the next clock
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b10

@cocotb.test()
async def test_writeback_stays_writeback(dut):
    """tests that decoder stays in WRITEBACK until the macro result is accepted"""

    dut._log.info("Testing writeback stays writeback...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)

    # receiver is not ready for the macro result
    dut.macro_resp_ready.value = 0

    # use scalar ADD to reach DISPATCH
    dut.macro_opcode.value = 0b00000
    dut.macro_req_valid.value = 1

    await Timer(1, units="ns")
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01

    # complete scalar micro op so decoder enters WRITEBACK
    dut.micro_resp_done.value = 1

    await Timer(1, units="ns")
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b10

    # completion pulse is over
    dut.micro_resp_done.value = 0

    # still not ready to accept result
    dut.macro_resp_ready.value = 0

    await ClockCycles(dut.clk, 3)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b10
    assert int(dut.macro_resp_valid.value) == 1

@cocotb.test()
async def test_writeback_to_decode(dut):
    """tests that accepting the macro result makes decoder WRITEBACK -> DECODE"""

    dut._log.info("Testing writeback to decode...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)

    # initially don't accept the result
    dut.macro_resp_ready.value = 0

    # send scalar ADD
    dut.macro_opcode.value = 0b00000
    dut.macro_req_valid.value = 1

    await Timer(1, units="ns")
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01

    # complete the scalar micro op
    dut.micro_resp_done.value = 1

    await Timer(1, units="ns")
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b10
    assert int(dut.macro_resp_valid.value) == 1

    # completion pulse is done
    dut.micro_resp_done.value = 0

    # receiver accepts the macro result
    dut.macro_resp_ready.value = 1

    await Timer(1, units="ns")

    # transition happens on next clock
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == STATE_DECODE

# 3. Read-Only Memory (ROM) Tests

@cocotb.test()
async def test_scalar_macro_conversion(dut):
    """tests that each scalar macro op is converted into the correct micro op"""

    dut._log.info("Testing scalar macro conversion...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    decode = dut.dut

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

    for opcode in scalar_ops:
        # reset before testing each opcode
        await reset_dut(dut)

        dut.macro_opcode.value = opcode
        dut.macro_u_x.value = 0x1234
        dut.macro_v_x.value = 0x5678
        dut.macro_req_valid.value = 1

        await Timer(1, units="ns")

        assert int(decode.state.value) == STATE_DECODE

        assert int(dut.micro_req_valid.value) == 1
        assert int(dut.micro_req_direct.value) == 1
        assert int(dut.micro_req_u1.value) == 0x1234
        assert int(dut.micro_req_v1.value) == 0x5678

        expected_micro_word = opcode & 0xF
        assert int(dut.micro_req_op.value) == expected_micro_word

        dut.macro_req_valid.value = 0


@cocotb.test()
async def test_vector_rom_ranges(dut):
    """tests that each vector macro op selects the correct ROM range"""

    dut._log.info("Testing vector ROM ranges...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    vector_ranges = [
        (0b01100, 0, 3),
        (0b01101, 3, 6),
        (0b01110, 6, 9),
        (0b01111, 9, 14),
        (0b10000, 14, 23),
        (0b10001, 23, 29),
        (0b10010, 29, 32),
        (0b10011, 32, 35),
    ]

    for opcode, start_addr, end_addr in vector_ranges:
        await reset_dut(dut)

        dut.micro_req_ready.value = 0
        dut.macro_opcode.value = opcode
        dut.macro_req_valid.value = 1

        await Timer(1, units="ns")
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

        assert int(decode.curr_addr.value) == start_addr
        assert int(decode.op_addr_end.value) == end_addr

        dut.macro_req_valid.value = 0


@cocotb.test()
async def test_rom_contents(dut):
    """tests the complete ROM instruction contents"""

    dut._log.info("Testing complete ROM contents...")

    decode = dut.dut

    expected = [
        (0,  0x0030, 0),
        (1,  0x04C0, 0),
        (2,  0x0950, 0),

        (3,  0x0031, 0),
        (4,  0x04C1, 0),
        (5,  0x0951, 0),

        (6,  0x0446, 0),
        (7,  0x0856, 0),
        (8,  0x0036, 0),

        (9,  0x0036, 0),
        (10, 0x04C6, 0),
        (11, 0x0956, 0),
        (12, 0x0010, 1),
        (13, 0x0020, 1),

        (14, 0x1946, 0),
        (15, 0x0936, 0),
        (16, 0x1046, 0),
        (17, 0x0CB6, 0),
        (18, 0x04D6, 0),
        (19, 0x1456, 0),
        (20, 0x00E1, 1),
        (21, 0x0551, 0),
        (22, 0x0A31, 0),

        (23, 0x101B, 0),
        (24, 0x122B, 1),
        (25, 0x11C7, 1),
        (26, 0x0206, 1),
        (27, 0x0616, 0),
        (28, 0x0A26, 0),

        (29, 0x0607, 0),
        (30, 0x0A87, 0),
        (31, 0x0187, 0),

        (32, 0x0036, 0),
        (33, 0x04C6, 0),
        (34, 0x0956, 0),
    ]

    for addr, micro_op, barrier in expected:
        await set_rom_addr(decode, addr)

        assert int(decode.micro_op_word.value) == micro_op
        assert int(decode.barrier.value) == barrier


@cocotb.test()
async def test_rom_default_entry(dut):
    """tests that an unused read-only memory address returns an empty non-barrier micro-operation."""

    dut._log.info("Testing unused ROM entry...")

    decode = dut.dut

    # read only
    await set_rom_addr(decode, 63)

    assert int(decode.micro_op_word.value) == 0
    assert int(decode.barrier.value) == 0