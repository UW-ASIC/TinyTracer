# reg_file tests

Cocotb tests for the register file (`src/exu/reg_file.sv`).

```
cd test/reg_file && make
```

The load is single-cycle: with `load` high, all six words (`load_u` to R0-R2, `load_v` to R3-R5) are written on one edge, as described in `docs/modules/exu/reg_file.md`.

For one test, add `TESTCASE=load_maps_correctly`.
