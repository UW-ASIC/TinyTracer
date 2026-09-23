---
description: "Ray Tracing Unit that sequences the ray-tracing algorithm with an FSM and issues instructions to the Decode Unit."
---

# `rtu` — Instantiates Ray Generator, Intersection Unit, and Shader Core

## Overview

This module uses a finite-state machine (FSM) to execute each step of the ray-tracing algorithm. Each step of the algorithm is a series of computations, where each computation is encoded as an instruction. These instructions are sent to the Decode Unit to decompose more complex instructions (like vector operations) into simple "micro-operations" that the individual scalar FUs can process. The RTU controls the Ray Generator, Intersection Unit, and Shader Core submodules to compute `SPP` sample colours per pixel. 

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `ADDR_WIDTH`  |     8      | SRAM address width             |
| `DATA_WIDTH`  |     16     | SRAM data width             |
| `WLEN`  |     16      | Word length              |
| `MACRO_W`  |     101     | Macro operation width             |
| `COLOUR_DEPTH`  |     8    | Bits per colour channel            |
| `SPP`  |     8      | Samples per pixel |
| `MAX_BOUNCES`  |     10      | Ray bounce limit |
| `BV_BASE`  |     `8'h00`      | Base SRAM address of the bounding volumes |
| `NUM_BV`  |     4      | Number of bounding volumes |
| `OBJ_BASE`  |     `8'h14`      | Base SRAM address of the primitives |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| `macro_if`  | Macro-op request and response channel to the Decode Unit |
| `sram_rd_if`  | SRAM read request and response channel |
| `colour_if`  | Sample pixel colour stream to the Accumulator |
| `render_if`  | Render strobe and image dimensions from the I/O Unit |

## Architecture Overview