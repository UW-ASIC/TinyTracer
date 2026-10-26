# Array multiplier verification

Standalone cocotb tests for the **raw unsigned 16 x 16 array core** in
[PR #14](https://github.com/UW-ASIC/TinyTracer/pull/14), reviewed at commit
`b51dbe4d91f34b8fec29ef5c272e8c52bc056011`.

## Scope

PR #14 has `multiplicand`, `multiplier_in`, and a registered 32-bit `product`.
It keeps `fu_if.server` in its port list but does not implement that interface.
The wrapper connects the real interface and drives its request inputs idle;
it does not modify the design or implement missing behavior for it.

The scoreboard uses Python's exact integer multiplication. Inputs are unsigned
bit patterns, including `0x8000` and `0xFFFF`; these are not negative numbers
in this core's contract. William's separate fixed-point reference model in
[PR #19](https://github.com/UW-ASIC/TinyTracer/pull/19) targets the future
signed/scaled 16-bit result, so it cannot directly score this raw output.

| Test | Checks |
| --- | --- |
| `directed_products` | All pairs from boundary values, powers of two, runs of ones, alternating patterns, and high-bit patterns; carry propagation and full product width |
| `random_back_to_back_products` | 5,000 deterministic random pairs, seed `0xA51C`, fresh operands every rising edge |
| `reset_during_activity` | Asynchronous active-low reset after nonzero results, reset held across an edge, release without an edge, and post-reset recovery |

Every product transaction also checks that output holds before the rising edge,
captures the current operands on that edge, and holds across the falling edge.
These are functional checks; no code-coverage percentage is claimed.

## Run

Use Verilator >= 5.006, Python 3.11, and the repository's pinned cocotb 1.9.2.
Icarus cannot compile the SystemVerilog interface used here. From the repo root:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r test/requirements.txt
git fetch https://github.com/UW-ASIC/TinyTracer.git refs/pull/14/head
git show FETCH_HEAD:src/exu/functional_units/multiplier.sv > /tmp/array-multiplier.sv
cd test/multiplier
make MULTIPLIER_RTL=/tmp/array-multiplier.sv
```

Use `TESTCASE=reset_during_activity` to run one test. When changing source paths,
remove `sim_build/` first or choose a fresh `SIM_BUILD` directory. With no
`MULTIPLIER_RTL` override the runner uses the repository's multiplier file;
the current `main` stub cannot compile against the raw-core wrapper.

The `Array multiplier core tests` workflow runs the same suite against the
immutable PR #14 commit above, checked out separately from the test sources.
It does not merge that PR or replace the repository's multiplier RTL.
Inspect `results.xml` as well as the build log; the workflow rejects missing,
empty, failed, or skipped test results.

## Integration test plan (not implemented by this raw-core suite)

The [multiplier specification](../../docs/modules/exu/functional_units/multiplier.md)
requires signed 16-bit operands, a 32-bit intermediate, format-selected shifts
of 7 or 14, rounding, saturation, and a result on `fu_if`.
A green raw-core run does **not** establish those requirements or full-chip
integration, timing closure, or RTL-to-GDS success.

Before adding FU-level checks, agree with the lead/designer on:

1. Whether the raw core will remain as a helper or the public multiplier ports
   will be replaced by `fu_if` alone.
2. The rounding rule for positive/negative halfway cases. PR #19 currently adds
   a positive half-unit bias before an arithmetic right shift (ties toward
   positive infinity); the prose specification only says "rounding".
3. Exact request acceptance and response timing. One-cycle latency is currently
   labelled an assumption in the docs.
4. How colour shifts of 8 and 10 will be selected; the documented 1-bit format
   selector currently selects only 7 and 14.

Then test both formats with zero, signed extrema, all sign combinations,
fractional rounding boundaries, saturation boundaries on both sides, and
random bit patterns against the agreed reference model. Also test valid/ready
acceptance, input changes after acceptance, idle bubbles, back-to-back traffic,
ignored opcodes, reset with pending work, and absence of spurious completions.
Compare both implementations with the same agreed numerical contract before
comparing synthesis area and timing.
