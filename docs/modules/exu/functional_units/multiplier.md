---
description: "Pipelined fixed-point multiplier."
---

# `multiplier` — Fixed-point multiplier

## Overview

This module is a pipelined fixed-point multiplier using the TBD algorithm (replace TBD with implemented algorithm later).

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `WLEN`  |     16      | Word length              |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| [`fu_if.server`](../../tinytracer_if.md#fu_if)  | Micro-op request and response channel from FU Control |

## Architecture Overview

The multiplier forms the full 32-bit product of two 16-bit operands, which never overflows. It then shifts the product right with rounding to get a 16-bit result, and clamps the result to `16'h7FFF` or `16'h8000` if it does not fit. `req_fmt` selects the shift (see [Number Formats](../../../encoding/number_format.md)):

| `req_fmt` | Shift | Use |
|:----:|:----:|----|
| 0 | 7 | POS $\times$ POS $\rightarrow$ POS |
| 1 | 14 | POS $\times$ DIR $\rightarrow$ POS, DIR $\times$ DIR $\rightarrow$ DIR |

The Shader Core's colour multiplies need shifts of 8 and 10 as well. How these are selected is still open (see [Instruction Encoding](../../../encoding/instruction.md)).

Latency: 1 cycle (assumed). The multiplier accepts a new request every cycle. Dot products alone are about 30% of the RTU's cycles, so a longer latency changes the frame time noticeably.
