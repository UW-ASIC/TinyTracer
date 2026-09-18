# Sample testbench for a Tiny Tapeout project

This is a sample testbench for a Tiny Tapeout project. It uses [cocotb](https://docs.cocotb.org/en/stable/) to drive the DUT and check the outputs.
See below to get started or for more information, check the [website](https://tinytapeout.com/hdl/testing/).

## Setting up

1. Edit [Makefile](Makefile) and modify `PROJECT_SOURCES` to point to your SystemVerilog files. Keep `tinytracer_pkg.sv` and `tinytracer_if.sv` first.
2. The RTL simulation runs on Verilator (5.036 or newer), because Icarus Verilog does not support the SystemVerilog interfaces used in `src`. The gate-level simulation still uses Icarus.

## How to run

To run the RTL simulation (Verilator):

```sh
make -B
```

To run it on Icarus instead, flatten the design first with [sv2v](https://github.com/zachjs/sv2v) and pass the result as the only source.

To run gatelevel simulation, first harden your project and copy `../runs/wokwi/results/final/verilog/gl/{your_module_name}.v` to `gate_level_netlist.v`.

Then run:

```sh
make -B GATES=yes
```

## How to view the VCD file

Using GTKWave
```sh
gtkwave tb.vcd tb.gtkw
```

Using Surfer
```sh
surfer tb.vcd
```
