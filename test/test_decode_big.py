# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from dataclasses import dataclass
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer, RisingEdge, ReadOnly

from test_decode_invariants import STATE_DECODE, reset_dut

# 4. Big Tests

BIG_SCALAR_OPS = (
    0b00000, 0b00001, 0b00010, 0b00011, 0b00100, 0b00101,
    0b00110, 0b00111, 0b01000, 0b01001, 0b01011,
)

BIG_VECTOR_RANGES = {
    0b01100: (0, 3),
    0b01101: (3, 6),
    0b01110: (6, 9),
    0b01111: (9, 14),
    0b10000: (14, 23),
    0b10001: (23, 29),
    0b10010: (29, 32),
    0b10011: (32, 35),
}

BIG_ROM = {
    0: (0x0030, 0), 1: (0x04C0, 0), 2: (0x0950, 0),
    3: (0x0031, 0), 4: (0x04C1, 0), 5: (0x0951, 0),
    6: (0x0446, 0), 7: (0x0856, 0), 8: (0x0036, 0),
    9: (0x0036, 0), 10: (0x04C6, 0), 11: (0x0956, 0),
    12: (0x0010, 1), 13: (0x0020, 1),
    14: (0x1946, 0), 15: (0x0936, 0), 16: (0x1046, 0),
    17: (0x0CB6, 0), 18: (0x04D6, 0), 19: (0x1456, 0),
    20: (0x00E1, 1), 21: (0x0551, 0), 22: (0x0A31, 0),
    23: (0x101B, 0), 24: (0x122B, 1), 25: (0x11C7, 1),
    26: (0x0206, 1), 27: (0x0616, 0), 28: (0x0A26, 0),
    29: (0x0607, 0), 30: (0x0A87, 0), 31: (0x0187, 0),
    32: (0x0036, 0), 33: (0x04C6, 0), 34: (0x0956, 0),
}

BIG_TRANSACTION_COUNT = 100


@dataclass(frozen=True)
class TestScenario:
    """A fixed decoder workload and fixed downstream timing behaviour."""

    name: str
    operations: tuple
    formats: tuple
    idle_gaps: tuple
    accept_ready: tuple
    scalar_waits: tuple
    vector_ready: tuple
    completion_delays: tuple
    response_stalls: tuple


def _workload(*phases):
    """Repeat explicit workload phases until exactly 100 transactions exist."""
    operations = tuple(op for phase in phases for op in phase)
    return (operations * ((BIG_TRANSACTION_COUNT + len(operations) - 1) // len(operations)))[
        :BIG_TRANSACTION_COUNT
    ]


SCALARS = BIG_SCALAR_OPS
VECTORS = tuple(BIG_VECTOR_RANGES)
ARITHMETIC = (0b00000, 0b00001, 0b00010, 0b00011, 0b01100, 0b01101)
GEOMETRY = (0b01110, 0b01111, 0b10000, 0b10001, 0b10010, 0b10011)
ALL_OPS = SCALARS + VECTORS

# These are intentionally written as workload descriptions rather than PRNG
# seeds.  A failure therefore names the kind of traffic that exposed it and
# does not depend on reproducing a random stream.
SCENARIOS = (
    TestScenario("scalar_then_vector", _workload(SCALARS, VECTORS), (0, 1), (0,), (1,), (0, 1, 2), (1, 1, 0, 1), (1, 2), (0, 1)),
    TestScenario("vector_then_scalar", _workload(VECTORS, SCALARS), (1, 0), (1, 0), (1,), (1, 0), (1, 0, 1), (2, 1), (1, 0)),
    TestScenario("alternating_formats", _workload(ALL_OPS), (0, 1), (0, 1, 2), (0, 1), (0, 2), (0, 1, 1, 1), (1, 2, 3), (0, 2)),
    TestScenario("format_zero_stream", _workload(ARITHMETIC, GEOMETRY, ALL_OPS), (0,), (0, 0, 1), (1, 0), (1,), (1, 0, 1), (1, 1, 2), (0, 1, 2)),
    TestScenario("format_one_stream", _workload(GEOMETRY, ARITHMETIC, ALL_OPS), (1,), (0, 1), (0, 1), (2, 1), (1, 1, 0), (2, 3, 1), (1, 2, 3)),
    TestScenario("scalar_bursts", _workload(SCALARS, SCALARS, VECTORS), (0, 1, 1), (0,), (1,), (0, 1, 3), (1, 0, 1), (1, 2), (0, 1)),
    TestScenario("vector_bursts", _workload(VECTORS, VECTORS, SCALARS), (1, 0, 0), (0,), (1,), (1, 2), (1, 1, 0, 1), (1, 3, 2), (0, 2)),
    TestScenario("geometry_heavy", _workload(GEOMETRY, GEOMETRY, ALL_OPS), (0, 1), (1, 0), (0, 1), (1,), (0, 1, 1, 1, 0), (2, 1, 3), (1, 0, 2)),
    TestScenario("arithmetic_heavy", _workload(ARITHMETIC, ARITHMETIC, ALL_OPS), (1, 0), (0, 1), (1, 0), (0, 1), (1, 0, 1, 1), (1, 2), (0, 1, 3)),
    TestScenario("continuous_input", _workload(ALL_OPS), (0, 1), (0,), (1,), (0,), (1, 1, 0), (1, 2), (0,)),
    TestScenario("gapped_input", _workload(ALL_OPS), (1, 0), (2, 1, 2), (1,), (1, 2), (1, 0, 1), (2, 3), (1, 2)),
    TestScenario("micro_backpressure", _workload(VECTORS, ALL_OPS), (0, 1), (0, 1), (0, 1), (1,), (0, 0, 1), (2, 1), (0, 1)),
    TestScenario("bursty_micro_ready", _workload(ALL_OPS, VECTORS), (1, 0), (0,), (1, 0), (2,), (0, 0, 1, 1), (1, 3, 2), (1, 0)),
    TestScenario("short_micro_latency", _workload(ALL_OPS), (0, 1), (0, 1), (1,), (0, 1), (1, 0, 1), (1,), (0, 2)),
    TestScenario("long_micro_latency", _workload(GEOMETRY, ALL_OPS), (1, 0), (1, 0), (0, 1), (3, 2), (1, 1, 0), (3, 3, 2), (1, 3)),
    TestScenario("response_backpressure", _workload(ALL_OPS), (0, 1), (0,), (1,), (1,), (1, 0, 1), (1, 2), (3, 2, 1, 3)),
    TestScenario("balanced_pipeline", _workload(ARITHMETIC, GEOMETRY, SCALARS), (0, 1, 1, 0), (0, 1), (1, 0), (0, 2, 1), (1, 0, 1, 1), (1, 2, 3), (0, 1, 2, 3)),
    TestScenario("barrier_pressure", _workload((0b10000, 0b10001), VECTORS, ALL_OPS), (1, 0), (0,), (1,), (0, 1), (1, 1, 1, 0), (3, 2, 1), (0, 1)),
    TestScenario("mixed_render_math", _workload(GEOMETRY, ARITHMETIC, SCALARS, VECTORS), (0, 0, 1, 1), (0, 1, 0, 2), (1, 0), (1, 2, 0), (1, 0, 1), (1, 3, 2), (0, 2, 1)),
    TestScenario("full_stress", _workload(ALL_OPS, tuple(reversed(ALL_OPS))), (0, 1), (0, 2, 1), (0, 1), (3, 0, 2), (0, 1, 0, 1, 1), (3, 1, 2), (3, 0, 2, 1)),
)


def _pattern(values, index):
    return values[index % len(values)]


async def run_big_test(dut, scenario):
    """Run one explicit 100-transaction workload with cycle-level checks."""
    decode = dut.dut

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    await Timer(1, units="ns")

    operations = scenario.operations

    opcode_hits = {opcode: 0 for opcode in ALL_OPS}
    rom_hits = {addr: 0 for addr in BIG_ROM}
    format_hits = {0: 0, 1: 0}
    micro_backpressure_cycles = 0
    macro_backpressure_cycles = 0
    barrier_stall_cycles = 0
    simultaneous_issue_done = 0

    for transaction, opcode in enumerate(operations):
        # Insert the workload's fixed idle gaps between macro transactions.
        dut.macro_req_valid.value = 0
        dut.macro_resp_ready.value = 0
        dut.micro_req_ready.value = 0
        dut.micro_resp_done.value = 0

        for _ in range(_pattern(scenario.idle_gaps, transaction)):
            await Timer(1, units="ns")

            assert int(decode.state.value) == STATE_DECODE
            assert int(dut.macro_req_ready.value) == 1
            assert int(dut.macro_resp_valid.value) == 0
            assert int(dut.micro_req_valid.value) == 0

            await RisingEdge(dut.clk)
            await Timer(1, units="ns")

        fmt = _pattern(scenario.formats, transaction)
        # Fixed, varied bit patterns exercise signs, zeroes, carries and dense data.
        operand_u = (0x1357 * (transaction + 1) + opcode * 0x0101) & 0xFFFF
        operand_v = (0xECA8 - transaction * 0x0421 - opcode * 0x0011) & 0xFFFF
        is_vector = opcode in BIG_VECTOR_RANGES

        opcode_hits[opcode] += 1
        format_hits[fmt] += 1

        # Present the next fixed macro request in idle DECODE.
        dut.macro_opcode.value = opcode
        dut.macro_fmt.value = fmt
        dut.macro_u_x.value = operand_u
        dut.macro_v_x.value = operand_v
        dut.macro_req_valid.value = 1
        dut.micro_req_ready.value = int(
            not is_vector or _pattern(scenario.accept_ready, transaction)
        )
        await Timer(1, units="ns")

        assert int(decode.state.value) == STATE_DECODE
        assert int(dut.macro_req_ready.value) == 1
        assert int(decode.macro_accept.value) == 1
        assert int(decode.rf_load.value) == 1

        if is_vector:
            assert int(dut.micro_req_valid.value) == 0
            assert int(decode.micro_issue.value) == 0
        else:
            # scalar acceptance is coupled to a ready direct micro request
            assert int(dut.micro_req_valid.value) == 1
            assert int(dut.micro_req_direct.value) == 1
            assert int(dut.micro_req_op.value) == (opcode & 0xF)
            assert int(dut.micro_req_u1.value) == operand_u
            assert int(dut.micro_req_v1.value) == operand_v
            assert int(decode.micro_issue.value) == 1

        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

        dut.macro_req_valid.value = 0
        assert int(decode.state.value) == 0b01
        assert int(decode.vector_macro.value) == int(is_vector)
        assert int(decode.fmt_reg.value) == fmt
        assert int(decode.rf_load.value) == 0

        if not is_vector:
            # Hold scalar completion for the scenario's prescribed clocks.
            assert int(decode.inflight.value) == 1
            for wait_cycle in range(_pattern(scenario.scalar_waits, transaction)):
                dut.micro_req_ready.value = _pattern(
                    scenario.vector_ready, transaction + wait_cycle
                )
                dut.micro_resp_done.value = 0
                await Timer(1, units="ns")

                assert int(decode.state.value) == 0b01
                assert int(decode.inflight.value) == 1
                assert int(dut.micro_req_valid.value) == 0
                assert int(decode.scalar_done.value) == 0

                await RisingEdge(dut.clk)
                await Timer(1, units="ns")

            # return the one accepted scalar micro operation
            dut.micro_req_ready.value = 0
            dut.micro_resp_done.value = 1
            await Timer(1, units="ns")

            assert int(decode.micro_issue.value) == 0
            assert int(decode.scalar_done.value) == 1

            await RisingEdge(dut.clk)
            await Timer(1, units="ns")

            dut.micro_resp_done.value = 0
            assert int(decode.state.value) == 0b10
            assert int(decode.inflight.value) == 0

        else:
            start_addr, end_addr = BIG_VECTOR_RANGES[opcode]
            expected_addr = start_addr
            expected_inflight = 0
            pending_completions = []
            dispatch_cycle = 0
            forced_backpressure = False

            assert int(decode.curr_addr.value) == start_addr
            assert int(decode.op_addr_end.value) == end_addr
            assert int(decode.inflight.value) == 0

            # model every vector DISPATCH cycle until natural completion
            while True:
                assert dispatch_cycle < 200

                if expected_addr == end_addr:
                    expected_word, expected_barrier = (0, 0)
                else:
                    expected_word, expected_barrier = BIG_ROM[expected_addr]
                completion = bool(
                    pending_completions
                    and pending_completions[0] <= dispatch_cycle
                )
                request_valid = (
                    expected_addr != end_addr
                    and (not expected_barrier or expected_inflight == 0)
                )

                # Force one stall per vector, then use the readiness waveform.
                if request_valid and not forced_backpressure:
                    request_ready = False
                    forced_backpressure = True
                elif completion and request_valid:
                    request_ready = True
                else:
                    request_ready = bool(_pattern(
                        scenario.vector_ready, transaction + dispatch_cycle
                    ))

                issue = request_valid and request_ready

                dut.micro_req_ready.value = int(request_ready)
                dut.micro_resp_done.value = int(completion)
                await Timer(1, units="ns")

                assert int(decode.state.value) == 0b01
                assert int(decode.curr_addr.value) == expected_addr
                assert int(decode.inflight.value) == expected_inflight
                assert int(decode.barrier.value) == expected_barrier
                assert int(dut.micro_req_valid.value) == int(request_valid)
                assert int(decode.micro_issue.value) == int(issue)
                assert int(decode.vector_done.value) == int(
                    expected_addr == end_addr and expected_inflight == 0
                )
                assert int(decode.scalar_done.value) == 0

                if expected_addr != end_addr:
                    assert int(dut.micro_req_op.value) == expected_word
                    assert int(dut.micro_req_direct.value) == 0

                if request_valid and not request_ready:
                    micro_backpressure_cycles += 1
                if expected_barrier and expected_inflight != 0:
                    barrier_stall_cycles += 1
                    assert int(dut.micro_req_valid.value) == 0
                if issue and completion:
                    simultaneous_issue_done += 1

                vector_done = expected_addr == end_addr and expected_inflight == 0

                await RisingEdge(dut.clk)
                await Timer(1, units="ns")

                if vector_done:
                    assert not pending_completions
                    assert int(decode.state.value) == 0b10
                    assert int(dut.macro_resp_valid.value) == 1
                    break

                if completion:
                    pending_completions.pop(0)
                    expected_inflight -= 1

                if issue:
                    rom_hits[expected_addr] += 1
                    expected_addr += 1
                    expected_inflight += 1
                    pending_completions.append(
                        dispatch_cycle + _pattern(
                            scenario.completion_delays,
                            transaction + dispatch_cycle,
                        )
                    )
                    pending_completions.sort()

                assert int(decode.state.value) == 0b01
                assert int(decode.curr_addr.value) == expected_addr
                assert int(decode.inflight.value) == expected_inflight

                dispatch_cycle += 1

            dut.micro_resp_done.value = 0
            dut.micro_req_ready.value = 0

        # hold each macro response for a deterministic amount of backpressure
        response_stalls = _pattern(scenario.response_stalls, transaction)
        dut.macro_resp_ready.value = 0
        for _ in range(response_stalls):
            await Timer(1, units="ns")

            assert int(decode.state.value) == 0b10
            assert int(dut.macro_resp_valid.value) == 1
            assert int(dut.macro_req_ready.value) == 0

            macro_backpressure_cycles += 1
            await RisingEdge(dut.clk)
            await Timer(1, units="ns")

        # accept the response before beginning the next transaction
        dut.macro_resp_ready.value = 1
        await Timer(1, units="ns")

        assert int(dut.macro_resp_valid.value) == 1

        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

        assert int(decode.state.value) == STATE_DECODE
        assert int(dut.macro_req_ready.value) == 1
        assert int(dut.macro_resp_valid.value) == 0

    # Every named workload remains broad enough to traverse the whole decoder.
    assert all(hits >= 1 for hits in opcode_hits.values())
    assert all(hits >= 1 for hits in rom_hits.values())
    if len(set(scenario.formats)) == 2:
        assert format_hits[0] >= 30
        assert format_hits[1] >= 30
    else:
        assert format_hits[scenario.formats[0]] == BIG_TRANSACTION_COUNT
    assert micro_backpressure_cycles >= len(BIG_VECTOR_RANGES) * 5
    assert macro_backpressure_cycles == sum(
        _pattern(scenario.response_stalls, i) for i in range(BIG_TRANSACTION_COUNT)
    )
    assert barrier_stall_cycles >= 10
    assert simultaneous_issue_done >= 10


def _scenario_test(index):
    async def test(dut):
        await run_big_test(dut, SCENARIOS[index])
    return test


# Explicit names make regressions describe the traffic condition, not a seed.
for _index, _scenario in enumerate(SCENARIOS):
    _test = _scenario_test(_index)
    _test.__name__ = f"test_decode_{_scenario.name}"
    _test.__qualname__ = _test.__name__
    _test.__doc__ = f"Run the fixed {_scenario.name} decoder workload."
    globals()[_test.__name__] = cocotb.test()(_test)

del _index, _scenario, _test
