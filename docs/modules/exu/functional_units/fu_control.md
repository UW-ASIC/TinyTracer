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
| [`micro_if.server`](../../tinytracer_if.md#micro_if)  | Micro-op request and response channel from the Decode Unit |

## Architecture Overview

When a micro-op is accepted (`micro.req_valid` and `micro.req_ready` both high), FU Control:

1. Selects the functional unit from the `MICROOP` field and remaps it to the unit's opcode (see [Instruction Encoding](../../../encoding/instruction.md#functional-units))
2. Takes the operands from register file read ports 1 and 2 (`RS1`, `RS2`), or, when `micro.req_direct` is high (scalar macro-ops), from `micro.req_u1` and `micro.req_v1`
3. Starts the unit over its `fu_if`, passing `micro.req_fmt` along. The multiplier uses it to pick the product shift (7 or 14) and the CORDIC unit to pick the square root mode (POS or DIR); the ALU ignores it
4. Remembers the micro-op's `RD`, and when the unit signals `resp_done`, writes `resp_result` to register `RD` and pulses `micro.resp_done`

The ALU and multiplier accept a new micro-op every cycle and take 1 cycle each. The CORDIC unit takes one micro-op at a time, for 17 to 23 cycles, so `micro.req_ready` is low for a CORDIC micro-op while the CORDIC unit is busy. With these latencies and the micro-op sequences in the ROM, at most one unit finishes in any cycle, so the single register file write port is enough.
