# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer, RisingEdge, ReadOnly

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

@cocotb.test()
async def test_barrier_stalls_until_inflight_zero(dut):
    """tests that a barrier waits for outstanding micro ops before issuing"""

    dut._log.info("Testing barrier stall and release...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)
    await Timer(1, units="ns")

    # accept DOT and enter its ROM sequence
    dut.macro_opcode.value = 0b01111
    dut.macro_req_valid.value = 1

    await Timer(1, units="ns")
    assert int(dut.macro_req_ready.value) == 1
    assert int(decode.macro_accept.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01
    assert int(decode.curr_addr.value) == 9
    assert int(decode.inflight.value) == 0

    # issue the three products without completing them yet
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

    # the barrier must hold even though the receiver stays ready
    for _ in range(2):
        assert int(decode.barrier.value) == 1
        assert int(dut.micro_req_op.value) == 0x0010
        assert int(dut.micro_req_valid.value) == 0
        assert int(decode.micro_issue.value) == 0

        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

        assert int(decode.curr_addr.value) == 12
        assert int(decode.inflight.value) == 3
        assert int(decode.state.value) == 0b01

    # return one product completion per clock while the barrier waits
    dut.micro_resp_done.value = 1
    for remaining in (2, 1, 0):
        assert int(dut.micro_req_valid.value) == 0
        assert int(decode.micro_issue.value) == 0

        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

        assert int(decode.inflight.value) == remaining
        assert int(decode.curr_addr.value) == 12
        assert int(decode.state.value) == 0b01
        assert int(dut.macro_resp_valid.value) == 0

    # with all products complete, the barrier ADD can now issue
    dut.micro_resp_done.value = 0
    await Timer(1, units="ns")

    assert int(dut.micro_req_valid.value) == 1
    assert int(decode.micro_issue.value) == 1
    assert int(dut.micro_req_op.value) == 0x0010

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.curr_addr.value) == 13
    assert int(decode.inflight.value) == 1
    assert int(decode.state.value) == 0b01

@cocotb.test()
async def test_micro_backpressure_stalls_and_resumes(dut):
    """tests that micro backpressure pauses dispatch until the receiver is ready"""

    dut._log.info("Testing micro backpressure and recovery...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)
    await Timer(1, units="ns")

    # accept VADD with micro requests initially held off
    dut.macro_opcode.value = 0b01100
    dut.macro_req_valid.value = 1

    await Timer(1, units="ns")
    assert int(decode.macro_accept.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01
    assert int(decode.curr_addr.value) == 0
    assert int(decode.inflight.value) == 0

    # accept the first micro op before applying backpressure
    dut.macro_req_valid.value = 0
    dut.micro_req_ready.value = 1
    await Timer(1, units="ns")

    assert int(dut.micro_req_valid.value) == 1
    assert int(decode.micro_issue.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.curr_addr.value) == 1
    assert int(decode.inflight.value) == 1

    # hold the pending request while the receiver is not ready
    dut.micro_req_ready.value = 0
    await Timer(1, units="ns")

    for _ in range(3):
        assert int(dut.micro_req_valid.value) == 1
        assert int(dut.micro_req_op.value) == 0x04C0
        assert int(decode.micro_issue.value) == 0

        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

        assert int(decode.curr_addr.value) == 1
        assert int(decode.inflight.value) == 1
        assert int(decode.state.value) == 0b01
        assert int(dut.macro_resp_valid.value) == 0

    # release backpressure and accept the pending micro op
    dut.micro_req_ready.value = 1
    await Timer(1, units="ns")

    assert int(dut.micro_req_valid.value) == 1
    assert int(dut.micro_req_op.value) == 0x04C0
    assert int(decode.micro_issue.value) == 1

    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.curr_addr.value) == 2
    assert int(decode.inflight.value) == 2
    assert int(decode.state.value) == 0b01

@cocotb.test()
async def test_rf_load_pulses_on_macro_accept(dut):
    """tests that rf_load asserts on macro acceptance and stays low while busy"""

    dut._log.info("Testing register file load pulse...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    await reset_dut(dut)
    await Timer(1, units="ns")

    # idle DECODE must not load the register file
    assert int(decode.rf_load.value) == 0
    for _ in range(2):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

        assert int(decode.state.value) == STATE_DECODE
        assert int(decode.macro_accept.value) == 0
        assert int(decode.rf_load.value) == 0

    # present VADD and check the load signal before acceptance
    dut.macro_opcode.value = 0b01100
    dut.macro_req_valid.value = 1
    await Timer(1, units="ns")

    assert int(decode.state.value) == STATE_DECODE
    assert int(dut.macro_req_ready.value) == 1
    assert int(decode.macro_accept.value) == 1
    assert int(decode.rf_load.value) == 1

    # accepting the macro ends the load pulse and enters DISPATCH
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")

    assert int(decode.state.value) == 0b01
    assert int(decode.rf_load.value) == 0

    # keeping macro valid high while busy must not cause another load
    for _ in range(3):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

        assert int(decode.state.value) == 0b01
        assert int(dut.macro_req_ready.value) == 0
        assert int(decode.macro_accept.value) == 0
        assert int(decode.rf_load.value) == 0

