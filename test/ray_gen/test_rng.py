# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

# Goal : Checks that rng output looks random enough 
# for the ray tracer plus a few more basic tests + compare to model.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from cocotb.triggers import FallingEdge
from reference_models.rng import RngModel

# One-cycle req pulse, then wait until the new value is visible.
async def pulse_req(dut):
    dut.req.value = 1
    await ClockCycles(dut.clk, 1)
    dut.req.value = 0
    await FallingEdge(dut.clk)

# Hold req high and count consecutive random numbers.
async def collect_numbers(dut, count):
    numbers = []
    dut.req.value = 1
    for _ in range(count):
        await FallingEdge(dut.clk)
        numbers.append(int(dut.rand_num.value))
    dut.req.value = 0
    return numbers

# Length of the longest streak of identical bits in a list of 0 or 1.
def longest_run(bits):
    longest = 1
    current = 1
    for i in range(1, len(bits)):
        if bits[i] == bits[i - 1]:
            current += 1
        else:
            current = 1
        if current > longest:
            longest = current
    return longest

@cocotb.test()
async def test_random_enough(dut):
    dut._log.info("RNG test started.")
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.rst_n.value = 0
    dut.req.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Create software LFSR
    model = RngModel()

    # Test 1: reset value is 1
    assert int(dut.rand_num.value) == model.rand_num == 1, f"Expected reset value 1, got {int(dut.rand_num.value)}"
    dut._log.info("Reset value test passed successfully!")
 
    # Test 2: LFSR holds its value while req is low
    await ClockCycles(dut.clk, 10)
    await FallingEdge(dut.clk)
    assert int(dut.rand_num.value) == model.rand_num, "LFSR shifted without req"
    dut._log.info("Hold test passed successfully!")

    # Test 3: one req pulse advances exactly 16 steps
    dut._log.info("Testing single 16-step advance...")
    await pulse_req(dut)
    expected = model.request()
    assert int(dut.rand_num.value) == expected, f"After one req expected {expected:#06x}, got {int(dut.rand_num.value):#06x}"
    dut._log.info("Single 16-step advance test passed successfully!")

    # Test if value still holds after an advance
    dut._log.info("Testing hold after advance...")
    await pulse_req(dut)
    model.request()
    await ClockCycles(dut.clk, 10)
    await FallingEdge(dut.clk)
    assert int(dut.rand_num.value) == model.rand_num, f"Moved without req after advance: expected {model.rand_num:#06x}, got {int(dut.rand_num.value):#06x}"
    dut._log.info("Hold after advance test passed successfully!")

    # Get one full period of all possible numbers (2^16 - 1)
    dut._log.info("Collecting 65535 random numbers...")
    count = 65535
    numbers = await collect_numbers(dut, count)

    # Test 4: Check if every number matches the model
    for i, n in enumerate(numbers):
        expected = model.request()
        assert n == expected, f"Number {i}: expected {expected:#06x}, got {n:#06x}"
        assert n != 0, f"Number {i}: LFSR locked up at zero"

    # Test 5: No repetition
    # The 16-bit LFSR should not repeat for the full period of possible numbers, 
    # so all of them should be different. Something probably is wrong if it repeats earlier than that.
    dut._log.info("Testing repetition...")
    repeats = count - len(set(numbers))
    dut._log.info(f"Repeated values: {repeats}")
    assert repeats == 0, f"Expected 0 repeated values, got {repeats} out of {count}"
    dut._log.info("Repetition test passed successfully!")

    # Test 6: Every bit should be about half ones, half zeros
    dut._log.info("Testing bit balance...")
    min_ones = int(count * 0.49)    # 49% to 51% tolerance - Please adjust it :)
    max_ones = int(count * 0.51)
    for bit in range(16):
        ones = 0
        for n in numbers:
            if (n >> bit) & 1 == 1:
                ones += 1
        dut._log.info(f"Bit {bit}: {ones} ones out of {count} (allowed {min_ones} to {max_ones})")
        assert min_ones <= ones <= max_ones, f"Bit {bit}: {ones} ones out of {count} (allowed {min_ones} to {max_ones})"
    dut._log.info("Bit balance test passed successfully!")

    # Test 7: No too long streaks of the same bit
    # Join all numbers into one string. A random string of this length has
    # a longest streak of about 20, so more than 32 means something is definitely wrong.
    dut._log.info("Testing streaks...")
    bits = []
    for n in numbers:
        for bit in range(16):
            bits.append((n >> bit) & 1)
    max_run = 32
    run = longest_run(bits)
    dut._log.info(f"Longest streak: {run} bits")
    assert run <= max_run, f"Expected a streak of at most {max_run} bits, got {run}"
    dut._log.info("Streak test passed successfully!")

    # Thought process for streak of 20...
    # Chances for the next k - 1 bits to match a "first" one is (1/2)^(k-1)
    # Chances for the bit before the "first" one is 1/2
    # Therefore the chances for a streak of k bits to start at one spot is (1/2) ^ k
    # Since there are about 65535 spots where a streak could start...
    # so number of streaks of length k or more should be n / (2^k)
    # 65535 * 16 bits = 1,048,560
    # (1,048,560) / (2 ^ 20) is about 1
    # A count of 1 is the cutoff: longer streaks are expected to appear less than once, shorter ones more than once.

    # Test 8: Reset mid-run returns the LSFR to 1
    dut._log.info("Testing reset mid-run...")
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)
    assert int(dut.rand_num.value) == 1, f"Reset did not restore 1, got {int(dut.rand_num.value):#06x}"
    dut._log.info("Reset mid-run test passed successfully!")

    dut._log.info("RNG Module test completed successfully")