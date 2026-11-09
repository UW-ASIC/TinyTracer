# booth_mul16 tests

Cocotb tests for the radix-4 Booth multiplier (`src/exu/functional_units/booth_mul16.sv`),
driven through its Tiny Tapeout-style wrapper `tt_um_booth_mul16`.

```
cd test/booth_mul16 && make
```

It runs on Icarus by default. Add `SIM=verilator` to use Verilator instead.

View the waveform with `gtkwave tb.vcd` or `surfer tb.vcd`.
