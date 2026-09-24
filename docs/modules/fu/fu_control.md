---
description: "Wrapper that instantiates TinyTracer's functional units: ALU, CORDIC, and multiplier."
---

# `fu_control` — Instantiates functional units

## Overview

This module is a top-level wrapper that instantiates the 3 functional units (ALU, CORDIC, and Multiplier).

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `WLEN`  |     16      | Word length              |
| `MICRO_W`  |     13    | Micro operation width             |
| `MICROOP_W`  |     4      | Micro opcode width |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |
| `rf_rdata1`  |     `WLEN`      | Register file read port 1 data |
| `rf_rdata2`  |     `WLEN`      | Register file read port 2 data |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `rf_wen`  |     1      | Register file write enable |
| `rf_waddr`  |     3      | Register file write address |
| `rf_wdata`  |     `WLEN`      | Register file write data |
| `rf_raddr1`  |     3      | Register file read port 1 address |
| `rf_raddr2`  |     3      | Register file read port 2 address |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| [`micro_if.server`](../tinytracer_if.md#micro_if)  | Micro-op request and response channel from the Decode Unit |

## Architecture Overview