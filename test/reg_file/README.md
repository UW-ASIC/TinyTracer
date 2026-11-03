# reg_file tests

Cocotb tests for the register file (`src/exu/reg_file.sv`).

```
cd test/reg_file && make
```

The load comes in two variants, selected with `REG_FILE_LOAD`:

- `multi` (default): `load` is held for 3 cycles and Decode presents one pair per cycle (cycle 1: `u.x`, `v.x` to R0, R3; cycle 2: `y` to R1, R4; cycle 3: `z` to R2, R5). This matches the current RTL.
- `single`: all six words are written on one edge, as described in `docs/modules/exu/reg_file.md`.

```
make REG_FILE_LOAD=single
```

The tests that only apply to the multicycle load are skipped in `single` mode. For one test, add `TESTCASE=load_maps_correctly`.
