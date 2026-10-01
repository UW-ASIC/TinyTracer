---
description: "Execution Unit that wraps the Decode Unit, micro-op ROM, register file, and functional units, and executes macro-ops issued by the RTU."
---

# `exu` — Instantiates Decode Unit, Register File, and Functional Units

## Overview

The Execution Unit (EXU) is TinyTracer's backend. It receives macro-ops from the RTU, executes them, and returns their results. The EXU instantiates the Decode Unit, Register File, and Functional Units.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `WLEN`  |     16      | Word length              |
| `MACRO_W`  |     102    | Macro operation width             |
| `MACROOP_W`  |     5      | Macro opcode width |
| `MICRO_W`  |     13    | Micro operation width             |
| `MICROOP_W`  |     4      | Micro opcode width |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| [`macro_if.server`](../tinytracer_if.md#macro_if)  | Macro-op request and response channel from the RTU, passed through to the Decode Unit |

## Architecture Overview

The EXU wires the macro-op channel to the [Decode Unit](decode.md) and the macro-op operands $\mathbf{\vec{u}}$ and $\mathbf{\vec{v}}$ to the [Register File](reg_file.md)'s parallel load. The Decode Unit holds the micro-op ROM and issues micro-ops to [FU Control](functional_units/fu_control.md) over `micro_if`. FU Control reads operands from the register file (or, for scalar macro-ops, from the request), starts the ALU, multiplier, or CORDIC unit, and writes each result back to the register file. The macro-op result is always R0-R2 of the register file.

A macro-op takes 3-65 cycles (see [Decode Unit](decode.md#timing-behaviour)). The EXU works on one macro-op at a time.
