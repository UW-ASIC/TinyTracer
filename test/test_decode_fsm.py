# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer, RisingEdge, ReadOnly

from test_decode_invariants import STATE_DECODE, reset_dut

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
async def test_reset_during_dispatch_with_inflight_ops(dut):
    """tests that reset clears outstanding work and returns DISPATCH to idle DECODE"""

    dut._log.info("Testing reset during dispatch with outstanding work...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)
    await Timer(1, units="ns")

    # accept VMUL with FMT_DIR so the stored values differ from reset
    dut.macro_opcode.value = 0b10011
    dut.macro_fmt.value = 1
    dut.macro_req_valid.value = 1
    await Timer(1, units="ns")

    assert int(decode.macro_accept.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01
    assert int(decode.curr_addr.value) == 32
    assert int(decode.inflight.value) == 0

    # issue one micro op and leave it outstanding
    dut.macro_req_valid.value = 0
    dut.micro_req_ready.value = 1
    await Timer(1, units="ns")

    assert int(decode.micro_issue.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01
    assert int(decode.curr_addr.value) == 33
    assert int(decode.op_addr_end.value) == 35
    assert int(decode.inflight.value) == 1
    assert int(decode.vector_macro.value) == 1
    assert int(decode.fmt_reg.value) == 1

    # reset active work using the existing handshake-clearing helper
    await reset_dut(dut)
    await Timer(1, units="ns")

    assert int(decode.state.value) == STATE_DECODE
    assert int(decode.curr_addr.value) == 0
    assert int(decode.op_addr_end.value) == 0
    assert int(decode.inflight.value) == 0
    assert int(decode.vector_macro.value) == 0
    assert int(decode.fmt_reg.value) == 0
    assert int(dut.macro_req_ready.value) == 1
    assert int(dut.macro_resp_valid.value) == 0
    assert int(dut.micro_req_valid.value) == 0
    assert int(decode.micro_issue.value) == 0
    assert int(decode.rf_load.value) == 0

    # abandoned work must not resume or produce a macro response
    for _ in range(2):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

        assert int(decode.state.value) == STATE_DECODE
        assert int(decode.inflight.value) == 0
        assert int(dut.micro_req_valid.value) == 0
        assert int(dut.macro_resp_valid.value) == 0


@cocotb.test()
async def test_reset_while_stalled_at_barrier(dut):
    """tests that reset clears a vector operation stalled at a barrier"""

    dut._log.info("Testing reset while stalled at a barrier...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)
    await Timer(1, units="ns")

    # accept DOT and enter its ROM sequence
    dut.macro_opcode.value = 0b01111
    dut.macro_fmt.value = 1
    dut.macro_req_valid.value = 1
    await Timer(1, units="ns")

    assert int(decode.macro_accept.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01
    assert int(decode.curr_addr.value) == 9
    assert int(decode.op_addr_end.value) == 14

    # issue the three products without returning any completions
    dut.macro_req_valid.value = 0
    dut.micro_req_ready.value = 1
    await Timer(1, units="ns")

    for issued in range(3):
        assert int(decode.curr_addr.value) == 9 + issued
        assert int(dut.micro_req_valid.value) == 1
        assert int(decode.micro_issue.value) == 1

        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

        assert int(decode.inflight.value) == issued + 1

    # confirm the decoder is stalled at the first DOT barrier
    assert int(decode.curr_addr.value) == 12
    assert int(decode.barrier.value) == 1
    assert int(decode.inflight.value) == 3
    assert int(dut.micro_req_valid.value) == 0
    assert int(decode.micro_issue.value) == 0
    assert int(decode.state.value) == 0b01

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.curr_addr.value) == 12
    assert int(decode.inflight.value) == 3
    assert int(decode.state.value) == 0b01

    # reset the decoder while the barrier is waiting
    await reset_dut(dut)
    await Timer(1, units="ns")

    assert int(decode.state.value) == STATE_DECODE
    assert int(decode.curr_addr.value) == 0
    assert int(decode.op_addr_end.value) == 0
    assert int(decode.inflight.value) == 0
    assert int(decode.vector_macro.value) == 0
    assert int(decode.fmt_reg.value) == 0
    assert int(dut.macro_req_ready.value) == 1
    assert int(dut.micro_req_valid.value) == 0
    assert int(dut.macro_resp_valid.value) == 0

    # abandoned barrier work must not restart after reset
    for _ in range(2):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

        assert int(decode.state.value) == STATE_DECODE
        assert int(decode.inflight.value) == 0
        assert int(dut.micro_req_valid.value) == 0
        assert int(dut.macro_resp_valid.value) == 0


@cocotb.test()
async def test_reset_during_writeback(dut):
    """tests that reset discards a pending macro response in WRITEBACK"""

    dut._log.info("Testing reset during writeback...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)
    await Timer(1, units="ns")

    # accept scalar ADD and its direct micro request together
    dut.macro_opcode.value = 0b00000
    dut.macro_fmt.value = 1
    dut.macro_req_valid.value = 1
    dut.micro_req_ready.value = 1
    dut.macro_resp_ready.value = 0
    await Timer(1, units="ns")

    assert int(decode.macro_accept.value) == 1
    assert int(dut.micro_req_valid.value) == 1
    assert int(decode.micro_issue.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01
    assert int(decode.inflight.value) == 1
    assert int(decode.vector_macro.value) == 0

    # complete the scalar micro op to enter WRITEBACK
    dut.macro_req_valid.value = 0
    dut.micro_req_ready.value = 0
    dut.micro_resp_done.value = 1
    await Timer(1, units="ns")

    assert int(decode.scalar_done.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    dut.micro_resp_done.value = 0
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b10
    assert int(decode.inflight.value) == 0
    assert int(dut.macro_resp_valid.value) == 1

    # hold the pending macro response for an additional clock
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b10
    assert int(dut.macro_resp_valid.value) == 1

    # reset before the receiver accepts the macro response
    await reset_dut(dut)
    await Timer(1, units="ns")

    assert int(decode.state.value) == STATE_DECODE
    assert int(decode.inflight.value) == 0
    assert int(decode.vector_macro.value) == 0
    assert int(decode.fmt_reg.value) == 0
    assert int(dut.macro_req_ready.value) == 1
    assert int(dut.macro_resp_valid.value) == 0
    assert int(dut.micro_req_valid.value) == 0

    # the discarded response must not reappear after reset
    for _ in range(2):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

        assert int(decode.state.value) == STATE_DECODE
        assert int(dut.macro_resp_valid.value) == 0
        assert int(dut.micro_req_valid.value) == 0


# CURRENTLY FAILS: RTL accepts a scalar macro even when its micro request cannot issue.
@cocotb.test()
async def test_scalar_macro_waits_for_micro_ready(dut):
    """tests that a scalar macro waits until its direct micro request can issue"""

    dut._log.info("Testing scalar macro backpressure...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)
    await Timer(1, units="ns")

    # present scalar MUL while the micro receiver is blocked
    dut.macro_opcode.value = 0b00110
    dut.macro_fmt.value = 1
    dut.macro_u_x.value = 0x1234
    dut.macro_v_x.value = 0x5678
    dut.macro_req_valid.value = 1
    dut.micro_req_ready.value = 0
    await Timer(1, units="ns")

    # the direct request must wait without consuming the macro
    for _ in range(3):
        assert int(decode.state.value) == STATE_DECODE
        assert int(dut.micro_req_valid.value) == 1
        assert int(dut.micro_req_direct.value) == 1
        assert int(dut.micro_req_op.value) == 0b0110
        assert int(dut.micro_req_u1.value) == 0x1234
        assert int(dut.micro_req_v1.value) == 0x5678
        assert int(dut.macro_req_ready.value) == 0
        assert int(decode.macro_accept.value) == 0
        assert int(decode.micro_issue.value) == 0
        assert int(decode.rf_load.value) == 0

        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

    # release backpressure so macro acceptance and micro issue occur together
    dut.micro_req_ready.value = 1
    await Timer(1, units="ns")

    assert int(dut.macro_req_ready.value) == 1
    assert int(decode.macro_accept.value) == 1
    assert int(decode.micro_issue.value) == 1
    assert int(decode.rf_load.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01
    assert int(decode.inflight.value) == 1
    assert int(decode.vector_macro.value) == 0
    assert int(decode.rf_load.value) == 0


@cocotb.test()
async def test_consecutive_vector_then_scalar(dut):
    """tests that a scalar macro runs correctly after a completed vector macro"""

    dut._log.info("Testing consecutive vector then scalar macros...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)
    await Timer(1, units="ns")

    # accept VADD as the first macro operation
    dut.macro_opcode.value = 0b01100
    dut.macro_req_valid.value = 1
    dut.macro_resp_ready.value = 0
    await Timer(1, units="ns")

    assert int(decode.macro_accept.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01
    assert int(decode.curr_addr.value) == 0
    assert int(decode.vector_macro.value) == 1

    # issue the first VADD micro op without a completion
    dut.macro_req_valid.value = 0
    dut.micro_req_ready.value = 1
    await Timer(1, units="ns")

    assert int(decode.micro_issue.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.curr_addr.value) == 1
    assert int(decode.inflight.value) == 1

    # issue the remaining micro ops while earlier work completes
    dut.micro_resp_done.value = 1
    for expected_addr in (2, 3):
        assert int(dut.micro_req_valid.value) == 1
        assert int(decode.micro_issue.value) == 1

        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

        assert int(decode.curr_addr.value) == expected_addr
        assert int(decode.inflight.value) == 1
        assert int(decode.state.value) == 0b01

    # complete the final outstanding VADD micro op
    dut.micro_req_ready.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    dut.micro_resp_done.value = 0
    await Timer(1, units="ns")

    assert int(decode.curr_addr.value) == 3
    assert int(decode.inflight.value) == 0
    assert int(decode.vector_done.value) == 1
    assert int(decode.state.value) == 0b01

    # vector completion enters WRITEBACK on the following edge
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b10
    assert int(dut.macro_resp_valid.value) == 1

    # accept the VADD response and return to DECODE
    dut.macro_resp_ready.value = 1
    await Timer(1, units="ns")

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == STATE_DECODE
    assert int(dut.macro_req_ready.value) == 1

    # accept scalar SUB and its direct micro request
    dut.macro_resp_ready.value = 0
    dut.macro_opcode.value = 0b00001
    dut.macro_u_x.value = 0x4321
    dut.macro_v_x.value = 0x1111
    dut.macro_req_valid.value = 1
    dut.micro_req_ready.value = 1
    await Timer(1, units="ns")

    assert int(decode.macro_accept.value) == 1
    assert int(dut.micro_req_valid.value) == 1
    assert int(dut.micro_req_direct.value) == 1
    assert int(dut.micro_req_op.value) == 0b0001
    assert int(decode.micro_issue.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01
    assert int(decode.vector_macro.value) == 0
    assert int(decode.inflight.value) == 1

    # complete the scalar operation and reach its WRITEBACK response
    dut.macro_req_valid.value = 0
    dut.micro_req_ready.value = 0
    dut.micro_resp_done.value = 1
    await Timer(1, units="ns")

    assert int(decode.scalar_done.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    dut.micro_resp_done.value = 0
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b10
    assert int(decode.inflight.value) == 0
    assert int(dut.macro_resp_valid.value) == 1


@cocotb.test()
async def test_consecutive_scalar_then_vector(dut):
    """tests that a vector macro runs correctly after a completed scalar macro"""

    dut._log.info("Testing consecutive scalar then vector macros...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)
    await Timer(1, units="ns")

    # accept scalar MUL and its direct micro request together
    dut.macro_opcode.value = 0b00110
    dut.macro_fmt.value = 0
    dut.macro_u_x.value = 0x1234
    dut.macro_v_x.value = 0x0002
    dut.macro_req_valid.value = 1
    dut.micro_req_ready.value = 1
    dut.macro_resp_ready.value = 0
    await Timer(1, units="ns")

    assert int(decode.macro_accept.value) == 1
    assert int(dut.micro_req_valid.value) == 1
    assert int(dut.micro_req_direct.value) == 1
    assert int(dut.micro_req_op.value) == 0b0110
    assert int(decode.micro_issue.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01
    assert int(decode.vector_macro.value) == 0
    assert int(decode.inflight.value) == 1

    # complete the scalar operation and enter WRITEBACK
    dut.macro_req_valid.value = 0
    dut.micro_req_ready.value = 0
    dut.micro_resp_done.value = 1
    await Timer(1, units="ns")

    assert int(decode.scalar_done.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    dut.micro_resp_done.value = 0
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b10
    assert int(decode.inflight.value) == 0
    assert int(dut.macro_resp_valid.value) == 1

    # accept the scalar response and return to DECODE
    dut.macro_resp_ready.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == STATE_DECODE
    assert int(dut.macro_req_ready.value) == 1

    # accept VSUB and load its vector ROM range
    dut.macro_resp_ready.value = 0
    dut.macro_opcode.value = 0b01101
    dut.macro_fmt.value = 1
    dut.macro_req_valid.value = 1
    await Timer(1, units="ns")

    assert int(decode.macro_accept.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01
    assert int(decode.vector_macro.value) == 1
    assert int(decode.curr_addr.value) == 3
    assert int(decode.op_addr_end.value) == 6
    assert int(decode.fmt_reg.value) == 1

    # issue the first VSUB micro op without a completion
    dut.macro_req_valid.value = 0
    dut.micro_req_ready.value = 1
    await Timer(1, units="ns")

    assert int(dut.micro_req_op.value) == 0x0031
    assert int(decode.micro_issue.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.curr_addr.value) == 4
    assert int(decode.inflight.value) == 1

    # issue the remaining VSUB micro ops as earlier work completes
    dut.micro_resp_done.value = 1
    for expected_addr, expected_op in ((5, 0x04C1), (6, 0x0951)):
        assert int(dut.micro_req_op.value) == expected_op
        assert int(dut.micro_req_valid.value) == 1
        assert int(decode.micro_issue.value) == 1
        assert int(decode.scalar_done.value) == 0

        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

        assert int(decode.curr_addr.value) == expected_addr
        assert int(decode.inflight.value) == 1
        assert int(decode.state.value) == 0b01

    # complete the final VSUB micro op at the end address
    dut.micro_req_ready.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    dut.micro_resp_done.value = 0
    await Timer(1, units="ns")

    assert int(decode.curr_addr.value) == 6
    assert int(decode.inflight.value) == 0
    assert int(decode.vector_done.value) == 1
    assert int(decode.state.value) == 0b01

    # vector completion reaches its own WRITEBACK response
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b10
    assert int(dut.macro_resp_valid.value) == 1


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
