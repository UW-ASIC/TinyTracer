# `rtu` — Instantiates Ray Generator, Intersection Unit, and Shader Core

## Overview

This module uses a finite-state machine (FSM) to execute each step of the ray-tracing algorithm. Each step of the algorithm is a series of computations, where each computation is encoded as an instruction. These instructions are sent to the Decode Unit to decompose more complex instructions (like vector operations) into simple "micro-operations" that the individual scalar FUs can process. The RTU controls the Ray Generator, Intersection Unit, and Shader Core submodules to compute `SPP` sample colours per pixel. 

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `ADDR_WIDTH`  |     9      | SRAM address width             |
| `DATA_WIDTH`  |     16     | SRAM data width             |
| `WLEN`  |     16      | Word length              |
| `MACRO_W`  |     101     | Macro operation width             |
| `COLOUR_DEPTH`  |     8    | Bits per colour channel            |

## Interface

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal               |
| `rst_n`  |     1     | Active-low reset              |
| `render`  |     1      | Enables the scene in SRAM to be rendered |
| `sram_req_ready`        |     1     | SRAM can accept read request           |
| `sram_resp_valid`        |     1     | SRAM read data valid           |
| `sram_resp_rdata`        |      `DATA_WIDTH`     | SRAM read data            |
| `macro_req_ready`        |     1     | Decode Unit can accept macro-ops          |
| `macro_resp_valid`        |     1    | Macro-op result is valid         |
| `macro_resp_result`        |      `3*WLEN`     | Macro-op result           |
| `sample_req_ready`        |      1     | Accumulator can accept pixel sample data           |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `sram_req_valid`  |     1      | SRAM read request valid              |
| `sram_req_raddr`  |     `ADDR_WIDTH`     | SRAM read address            |
| `sram_resp_ready`  |     1      | RTU can accept SRAM read data            |
| `macro_req_valid`  |     1      | Macro-op valid            |
| `macro_req_op`        |     `MACRO_W`     | Macro-op           |
| `macro_resp_ready`        |     1     | RTU can accept macro-op result           |
| `sample_req_valid`        |     1     | RTU pixel sample data valid           |
| `sample_req_colour`        |     `3*COLOUR_DEPTH`     | RTU pixel sample data           |

## Architecture Overview