![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

# TinyTracer

TinyTracer is a small ray-tracing graphics chip for [Tiny Tapeout](https://tinytapeout.com), designed by the University of Waterloo ASIC Design Team. A host device sends a 3D scene over UART, the chip renders it one pixel at a time with up to 32 samples per pixel and 8 bounces, and streams the pixels back over the same link.

- Design documentation: https://uw-asic.github.io/TinyTracer/ (sources in [docs](docs), built with MkDocs)
- Tiny Tapeout datasheet: [docs/info.md](docs/info.md)

## Repository layout

| Path | Contents |
|----|----|
| [src](src) | SystemVerilog RTL. `tinytracer_pkg.sv` holds shared constants and types, `tinytracer_if.sv` the interfaces between modules, and `tt_um_tinytracer.sv` the top module |
| [test](test) | cocotb testbench (see [test/README.md](test/README.md)) |
| [sim](sim) | C++ software model of the chip, which renders a scene file with the chip's 16-bit arithmetic and counts cycles |
| [docs](docs) | Design documentation |
| [info.yaml](info.yaml) | Tiny Tapeout project information: source files, top module, pinout |

## Running

- RTL simulation: `cd test && make -B` (needs Verilator and cocotb; see [test/README.md](test/README.md))
- Documentation: `pip install -r docs/requirements.txt`, then `mkdocs serve`
- Software model: `g++ -O2 -std=c++17 sim/tinytracer_sim.cpp -o sim/tinytracer_sim`, then `sim/tinytracer_sim sim/scene_demo.txt`

Every file in `src` refers to package items by qualified name (`tinytracer_pkg::WLEN`), because the Yosys version that the Tiny Tapeout flow uses does not accept `import tinytracer_pkg::*;`.
