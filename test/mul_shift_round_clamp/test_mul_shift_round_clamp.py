# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

# Cocotb tests for the fixed-point multiply
# (src/exu/functional_units/mul_shift_round_clamp.sv): Booth product, shift right by 7
# or 14, round half up, clamp. Run with `make` in this folder.

import random

import cocotb
from cocotb.triggers import Timer

# 200 values of A and 200 of B; every pair is checked with both shifts.
N_VALUES = 200


def s16(x):
    """16-bit pattern -> signed value."""
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x


def fixed_mul(a, b, dir_):
    """Reference model: what mul_shift_round_clamp must output for signed a, b."""
    s = 14 if dir_ else 7
    r = (a * b + (1 << (s - 1))) >> s  # Python's >> rounds down, like an arithmetic shift
    return max(-32768, min(32767, r))


# (a, b, dir, expected, what it checks). POS 1.0 = 128, DIR 1.0 = 16384.
DIRECTED = [
    (192, 256, 0, 384, "POS 1.5 x 2.0 = 3.0"),
    (-128, -128, 0, 128, "POS -1.0 x -1.0 = 1.0"),
    (8192, 8192, 1, 4096, "DIR 0.5 x 0.5 = 0.25"),
    (16384, -16384, 1, -16384, "DIR 1.0 x -1.0 = -1.0"),
    (1280, 8192, 1, 640, "POS 10.0 x DIR 0.5 = POS 5.0"),
    (1, 64, 0, 1, "+0.5 LSB rounds up to 1"),
    (-1, 64, 0, 0, "-0.5 LSB rounds up to 0"),
    (1, 63, 0, 0, "just under +0.5 LSB rounds down"),
    (-1, 65, 0, -1, "just past -0.5 LSB rounds to -1"),
    (1, 8192, 1, 1, "+0.5 LSB rounds up to 1 (shift 14)"),
    (-1, 8192, 1, 0, "-0.5 LSB rounds up to 0 (shift 14)"),
    (2047, 2048, 0, 32752, "POS 15.99 x 16.0 = 255.875 fits"),
    (2048, 2048, 0, 32767, "POS 16.0 x 16.0 = 256.0 clamps to 255.99"),
    (192, 21845, 0, 32767, "rounds up to 32768, clamps to 32767"),
    (32767, 32767, 0, 32767, "POS 255.99^2 clamps to max"),
    (-32768, 32767, 0, -32768, "POS -256 x 255.99 clamps to min"),
    (-32768, -32768, 1, 32767, "DIR -2.0 x -2.0 = 4.0 clamps to max"),
    (-32768, 16384, 1, -32768, "DIR -2.0 x 1.0 = -2.0 is the min, no clamp"),
    (16384, 16384, 1, 16384, "DIR 1.0 x 1.0 = 1.0"),
    (0, -32768, 0, 0, "0 x anything = 0"),
]

# Values that tend to break multipliers, and the fixed-point 1.0s.
CORNER_VALUES = (
    [0, 1, -1, 2, -2, 3, -3, 128, -128, 192, 256, 16384, -16384, 8192]
    + [32767, -32768, 32766, -32767]
    + [v for k in range(15) for v in (1 << k, (1 << k) - 1, -(1 << k), 1 - (1 << k))]
    + [s16(x) for x in (0x5555, 0xAAAA, 0x3333, 0xCCCC, 0x6DB6, 0x9249)]
)


def make_values(seed):
    """N_VALUES distinct signed 16-bit values: CORNER_VALUES, then random ones.

    The random ones have a random bit length, so small values, where the
    shifted product fits, are as common as large ones, where it clamps. A fixed
    seed gives the same list every run, so a failure can be rerun.
    """
    values = list(dict.fromkeys(CORNER_VALUES))  # drop repeats, keep order
    assert len(values) <= N_VALUES
    rng = random.Random(seed)
    seen = set(values)
    while len(values) < N_VALUES:
        k = rng.randint(0, 14)
        v = rng.randint(1 << k, (2 << k) - 1) * rng.choice((1, -1))
        if v not in seen:
            seen.add(v)
            values.append(v)
    return values


A_VALUES = make_values(seed=3)
B_VALUES = make_values(seed=4)


async def multiply(dut, a, b, dir_):
    """Drive the inputs and return mul_shift_round_clamp's result as a signed value."""
    dut.a.value = a & 0xFFFF
    dut.b.value = b & 0xFFFF
    dut.dir.value = dir_
    await Timer(1, "ns")  # positional unit works on cocotb 1.9 and 2.x
    return s16(int(dut.result.value))


@cocotb.test()
async def test_directed(dut):
    """Hand-picked rounding and clamping cases, with what each one checks."""
    for a, b, dir_, expected, what in DIRECTED:
        assert fixed_mul(a, b, dir_) == expected, f"model disagrees with table: {what}"
        got = await multiply(dut, a, b, dir_)
        assert got == expected, f"{what}: {a} * {b}, dir={dir_}: got {got}, expected {expected}"


@cocotb.test()
async def test_all_pairs(dut):
    """Every A times every B, with both shifts, against the reference model."""
    for dir_ in (0, 1):
        s = 14 if dir_ else 7
        counts = {"fits": 0, "clamp max": 0, "clamp min": 0, "+half": 0, "-half": 0}
        for a in A_VALUES:
            for b in B_VALUES:
                expected = fixed_mul(a, b, dir_)
                got = await multiply(dut, a, b, dir_)
                assert got == expected, f"{a} * {b}, dir={dir_}: got {got}, expected {expected}"

                # What kind of case this was, to show the test reaches all of them
                p = a * b
                r = (p + (1 << (s - 1))) >> s
                counts["clamp max" if r > 32767 else "clamp min" if r < -32768 else "fits"] += 1
                if p & ((1 << s) - 1) == 1 << (s - 1):  # exactly half an LSB
                    counts["+half" if p > 0 else "-half"] += 1

        dut._log.info(f"dir={dir_} (shift {s}): {len(A_VALUES) * len(B_VALUES)} pairs, {counts}")
        for kind, n in counts.items():
            assert n > 0, f"dir={dir_}: no '{kind}' case among the values"
