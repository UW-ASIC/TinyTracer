---
description: "Top-level Tiny Tapeout module for TinyTracer, instantiating the SRAM controller, RTU, Execution Unit, Accumulator, and I/O Unit."
---

# `tt_um_tinytracer` — Top-Level Module for TinyTracer

## Overview

This module instantiates the SRAM, SRAM controller, RTU, Execution Unit (EXU), Accumulator, and I/O Unit. The EXU in turn instantiates the Decode Unit, Register File, and FU Control Unit (see [`exu`](exu/exu.md)).

TinyTracer targets the IHP SG13CMOS5L process (`ihp-sg13cmos5l`), which Tiny Tapeout's IHP shuttles use, with a 25 MHz clock (40 ns). The scene SRAM has 512 words of 16 bits and is wrapped by [`scene_sram`](sram/scene_sram.md): IHP's ready-made `RM_IHPSG13_1P_512x16_c2_bm_bist` macro fits it, but no macro is instantiated yet.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `ADDR_WIDTH`  |     9      | Width of SRAM addresses               |
| `DIM_WIDTH`   |     12     | Width of the image width and height   |
| `DATA_WIDTH`  |     16     | Width of SRAM data words              |
| `MAX_SPP`     |     32     | Largest samples per pixel; the samples per pixel of a render come from the scene header |
| `SPP_LOG2_W`  |     3      | Width of $\log_2$ of the samples per pixel |
| `MAX_BOUNCES` |     8      | Ray bounce limit                      |
| `COLOUR_DEPTH` |     8      | Bits per pixel colour channel           |
| `SAMPLE_DEPTH` |     12      | Bits per sample colour channel           |
| `POS_FRAC`    |     7      | Fractional bits of the POS format (Q9.7) |
| `DIR_FRAC`    |     14     | Fractional bits of the DIR format (Q2.14) |
| `MACRO_W`     |    102     | Width of macro-op encoding            |
| `WLEN`        |     16     | Word length                           |

## Ports

The module has the standard Tiny Tapeout ports.

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal               |
| `rst_n`  |     1     | Active-low reset              |
| `ena`  |     1     | High while the design is powered; unused |
| `ui_in`  |     8     | Dedicated inputs: `ui_in[3]` is `uart_rx`, which receives scene data from the host device; the others are unused |
| `uio_in`  |     8     | Bidirectional pins, input path; unused |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `uo_out`  |     8      | Dedicated outputs: `uo_out[4]` is `uart_tx`, which streams pixel colours back to the host device; the others are 0 |
| `uio_out`  |     8      | Bidirectional pins, output path; 0 |
| `uio_oe`  |     8      | Bidirectional pins, output enables; 0, so all are inputs |

The I/O Unit's `clkdiv_ctl` and `clkdiv_data` have no pins yet, and the top module ties them to 0, which leaves the clock divider settings unchanged.

## Architecture Overview

The top module connects its six blocks through interface instances (see [`tinytracer_if`](tinytracer_if.md)):

| Instance | Module | Connections |
|----|----|----|
| `u_io` | [`io`](io/io.md) | `render_cmd` (to the RTU), `sram_wr` (to the SRAM controller), `pixel` (from the Accumulator), pins |
| `u_sram_control` | [`sram_control`](sram/sram_control.md) | `sram_wr`, `sram_rd`, and the SRAM signals `sram_wen`, `sram_addr`, `sram_din`, `sram_dout` |
| `u_scene_sram` | [`scene_sram`](sram/scene_sram.md) | The SRAM signals |
| `u_rtu` | [`rtu`](rtu/rtu.md) | `render_cmd`, `sram_rd`, `macro` (to the EXU), `sample` (to the Accumulator), `spp_log2` |
| `u_exu` | [`exu`](exu/exu.md) | `macro` |
| `u_accumulator` | [`accumulator`](accumulator/accumulator.md) | `sample`, `spp_log2`, `pixel` |

`sample` is a `colour_if` with `W` = `SAMPLE_DEPTH` and `pixel` one with `W` = `COLOUR_DEPTH`.

Below the top module, the wrapper modules instantiate their own blocks: [`io`](io/io.md) instantiates `uart` and `clkdiv`, [`rtu`](rtu/rtu.md) instantiates the Ray Generator (which instantiates the RNG), Intersection Unit, and Shader Core, and [`exu`](exu/exu.md) instantiates the Decode Unit, Register File, and FU Control, which instantiates the ALU, multiplier, and CORDIC unit. Every module can therefore be developed in its own file against these connections.
