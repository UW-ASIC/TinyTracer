# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

# Cocotb tests for the clock divider (src/io/clkdiv.sv).
# Run with `make` in this folder. clkdiv is the toplevel here, so we drive
# b, c, q, clk and rst_n directly.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, ReadOnly, RisingEdge
from reference_models.clkdiv import ClkdivRef

CLK_PERIOD_NS = 40  # 25 MHz

# Settings from docs/modules/io/clkdiv.md. c is negative, so the 8-bit port
# holds the two's complement form (-18 -> 238, -1 -> 255).
B_115200, C_115200 = 104, 238
B_230400, C_230400 = 43, 238


async def start_clkdiv(dut, b: int, c: int) -> None:
    # Start the clock, hold reset with these settings, then let it run.
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, units="ns").start())

    dut.rst_n.value = 0
    dut.b.value = b
    dut.c.value = c
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1


async def check_against_ref(dut, ref: ClkdivRef, cycles: int, label: str = "") -> None:
    # Step the reference and the DUT together and check q matches every cycle.
    # We read in ReadOnly so we see the values after the edge. Then q is the
    # state after i edges, which is what ref.q is after i ticks, so compare
    # first and tick after.
    for i in range(cycles):
        await ReadOnly()
        ref_output = ref.q
        dut_output = int(dut.q.value)
        assert ref_output == dut_output, (
            f"Mismatch at cycle {i}{label}: ref={ref_output}, dut={dut_output}"
        )
        ref.tick()
        await RisingEdge(dut.clk)


async def measure_ratio(dut, cycles: int) -> float:
    # Count output toggles over `cycles`. Each toggle is half a period, so
    # toggles / 2 is the number of full periods.
    toggles = 0
    prev_q = int(dut.q.value)
    for _ in range(cycles):
        curr_q = int(dut.q.value)
        if curr_q != prev_q:
            toggles += 1
        prev_q = curr_q
        await ClockCycles(dut.clk, 1)

    return (toggles / 2) / cycles


@cocotb.test()
async def test_clkdiv_reset(dut):
    # q should be 0 while reset is held.
    dut._log.info("clkdiv reset")

    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, units="ns").start())

    dut.rst_n.value = 0
    dut.b.value = B_115200
    dut.c.value = C_115200
    await ClockCycles(dut.clk, 5)

    await ReadOnly()
    assert dut.q.value == 0, f"Expected q=0 after reset, got {dut.q.value}"
    dut._log.info("✓ Output is 0 after reset")

    await RisingEdge(dut.clk)  # can't write inside ReadOnly
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)


@cocotb.test()
async def test_clkdiv_basic_115200(dut):
    # 2000 cycles at the 115,200 baud settings, checked against the model.
    dut._log.info("115,200 baud (b=104, c=-18)")

    await start_clkdiv(dut, B_115200, C_115200)
    await check_against_ref(dut, ClkdivRef(B_115200, C_115200), 2000)
    dut._log.info("✓ All 2000 cycles match reference model")


@cocotb.test()
async def test_clkdiv_basic_230400(dut):
    # 2000 cycles at the 230,400 baud settings, checked against the model.
    dut._log.info("230,400 baud (b=43, c=-18)")

    await start_clkdiv(dut, B_230400, C_230400)
    await check_against_ref(dut, ClkdivRef(B_230400, C_230400), 2000)
    dut._log.info("✓ All 2000 cycles match reference model")


@cocotb.test()
async def test_clkdiv_frequency_115200(dut):
    # Output should be about 1.844 MHz at 115,200 baud.
    dut._log.info("Frequency check: 115,200 baud")

    await start_clkdiv(dut, B_115200, C_115200)
    await ClockCycles(dut.clk, 1)  # skip the first cycle after reset

    measured_ratio = await measure_ratio(dut, 100_000)

    # 1.844 MHz / 25 MHz = 0.07376
    expected_ratio = 1.844e6 / 25e6
    error_percent = abs(measured_ratio - expected_ratio) / expected_ratio * 100

    dut._log.info(f"Measured frequency ratio: {measured_ratio:.6f}")
    dut._log.info(f"Expected frequency ratio: {expected_ratio:.6f}")
    dut._log.info(f"Error: {error_percent:.2f}%")

    # 1% is plenty of room for finite sampling
    assert error_percent < 1.0, (
        f"Frequency error {error_percent:.2f}% exceeds 1% tolerance"
    )
    dut._log.info("✓ Frequency within tolerance")


@cocotb.test()
async def test_clkdiv_frequency_230400(dut):
    # Output should be about 3.689 MHz at 230,400 baud.
    dut._log.info("Frequency check: 230,400 baud")

    await start_clkdiv(dut, B_230400, C_230400)
    await ClockCycles(dut.clk, 1)  # skip the first cycle after reset

    measured_ratio = await measure_ratio(dut, 100_000)

    # 3.689 MHz / 25 MHz = 0.14756
    expected_ratio = 3.689e6 / 25e6
    error_percent = abs(measured_ratio - expected_ratio) / expected_ratio * 100

    dut._log.info(f"Measured frequency ratio: {measured_ratio:.6f}")
    dut._log.info(f"Expected frequency ratio: {expected_ratio:.6f}")
    dut._log.info(f"Error: {error_percent:.2f}%")

    assert error_percent < 1.0, (
        f"Frequency error {error_percent:.2f}% exceeds 1% tolerance"
    )
    dut._log.info("✓ Frequency within tolerance")


@cocotb.test()
async def test_clkdiv_parameter_change(dut):
    # Run with one setting, switch b and c mid-run, and keep checking.
    dut._log.info("Parameter switching")

    await start_clkdiv(dut, B_115200, C_115200)
    ref = ClkdivRef(B_115200, C_115200)
    await check_against_ref(dut, ref, 1000)
    dut._log.info("✓ First 1000 cycles verified with (104, -18)")

    # No reset this time, so the accumulator carries over
    dut.b.value = B_230400
    dut.c.value = C_230400
    ref.set_params(B_230400, C_230400)
    await check_against_ref(dut, ref, 1000, label=" after parameter change")
    dut._log.info("✓ Second 1000 cycles verified with (43, -18)")


@cocotb.test()
async def test_clkdiv_edge_case_b_equals_neg_c(dut):
    # b = -c gives a divide by 4.
    dut._log.info("Edge case: b = -c")

    await start_clkdiv(dut, 18, -18 & 0xFF)
    await check_against_ref(dut, ClkdivRef(18, -18 & 0xFF), 1000)

    measured_ratio = await measure_ratio(dut, 1000)
    expected_ratio = 1.0 / 4  # 6.25 MHz / 25 MHz

    dut._log.info(f"Measured ratio: {measured_ratio:.6f}, Expected: {expected_ratio:.6f}")
    assert abs(measured_ratio - expected_ratio) < 0.01, "Ratio mismatch for b=-c case"
    dut._log.info("✓ Edge case b = -c verified")


@cocotb.test()
async def test_clkdiv_slowest_legal(dut):
    # b=126, c=-1 is the slowest legal setting (b - c = 127, the max).
    dut._log.info("Slowest legal: b=126, c=-1")

    await start_clkdiv(dut, 126, -1 & 0xFF)
    await check_against_ref(dut, ClkdivRef(126, -1 & 0xFF), 5000)
    dut._log.info("✓ Slowest legal setting verified")


@cocotb.test()
async def test_clkdiv_largest_negative_c(dut):
    # b=63, c=-63 is the biggest |c| we allow (b = -c).
    dut._log.info("Largest negative c: b=63, c=-63")

    await start_clkdiv(dut, 63, -63 & 0xFF)
    await check_against_ref(dut, ClkdivRef(63, -63 & 0xFF), 2000)
    dut._log.info("✓ Largest negative c verified")


@cocotb.test()
async def test_clkdiv_duty_cycle(dut):
    # Output should spend about half its time high.
    dut._log.info("Duty cycle check")

    await start_clkdiv(dut, B_115200, C_115200)

    cycles_high = 0
    cycles_low = 0
    for _ in range(10000):
        if int(dut.q.value):
            cycles_high += 1
        else:
            cycles_low += 1
        await ClockCycles(dut.clk, 1)

    duty_cycle = cycles_high / (cycles_high + cycles_low)
    dut._log.info(f"Duty cycle: {duty_cycle:.3f}")

    assert 0.40 < duty_cycle < 0.60, f"Duty cycle {duty_cycle} outside range"
    dut._log.info("✓ Duty cycle OK")


@cocotb.test()
async def test_clkdiv_period_jitter(dut):
    # Toggles can't be perfectly even, since the divider works in whole cycles.
    # But the gaps should never differ by more than one cycle.
    dut._log.info("Toggle spacing check")

    await start_clkdiv(dut, B_230400, C_230400)

    gaps = []
    prev_q = int(dut.q.value)
    cycles_since_toggle = None  # None until the first toggle, so we skip the partial gap
    for _ in range(5000):
        curr_q = int(dut.q.value)
        if cycles_since_toggle is not None:
            cycles_since_toggle += 1
        if curr_q != prev_q:
            if cycles_since_toggle is not None:
                gaps.append(cycles_since_toggle)
            cycles_since_toggle = 0
        prev_q = curr_q
        await ClockCycles(dut.clk, 1)

    assert len(gaps) > 10, f"Only {len(gaps)} toggle gaps measured"

    # Gaps should be the floor or ceiling of the average, so the spread is at
    # most 1. Anything bigger is a real bug.
    avg_gap = sum(gaps) / len(gaps)
    spread = max(gaps) - min(gaps)

    dut._log.info(f"Avg gap: {avg_gap:.2f}, min: {min(gaps)}, max: {max(gaps)}")

    assert spread <= 1, f"Toggle gap spread {spread} cycles exceeds 1 cycle"
    dut._log.info("✓ Toggle spacing consistent")


@cocotb.test()
async def test_clkdiv_reset_accumulator(dut):
    # Reset in the middle of a run and make sure it picks up cleanly after.
    dut._log.info("Reset at various states")

    b, c = 60, 200  # c = -56, so b has to be at least 56
    await start_clkdiv(dut, b, c)

    # 256 cycles hits every accumulator value
    await check_against_ref(dut, ClkdivRef(b, c), 256, label=" before reset")

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 1)
    await ReadOnly()
    assert dut.q.value == 0, "Not 0 during reset"

    await RisingEdge(dut.clk)  # can't write inside ReadOnly
    dut.rst_n.value = 1

    # The next edge is the first real one after reset
    await check_against_ref(dut, ClkdivRef(b, c), 500, label=" after reset")
    dut._log.info("✓ Reset behavior OK")


@cocotb.test()
async def test_clkdiv_long_term(dut):
    # 50k cycles, to catch anything that only shows up after a while.
    dut._log.info("Long-term stability check")

    await start_clkdiv(dut, B_115200, C_115200)
    await check_against_ref(dut, ClkdivRef(B_115200, C_115200), 50_000)
    dut._log.info("✓ Stable over 50k cycles")
