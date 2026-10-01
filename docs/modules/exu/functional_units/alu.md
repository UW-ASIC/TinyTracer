---
description: "Fixed-point ALU supporting addition, subtraction, and comparison."
---

# `alu` — Fixed-point ALU

## Overview

This module is a fixed-point ALU supporting addition, subtraction, and comparison operations. It works on raw 16-bit two's complement values, so it is the same for POS and DIR numbers (see [Number Formats](../../../encoding/number_format.md)).

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

* `ALU_ADD` and `ALU_SUB` clamp: a result that does not fit in 16 bits is replaced by `16'h7FFF` or `16'h8000`
* `ALU_EQ`, `ALU_NE`, `ALU_LT`, and `ALU_GE` return 1 if the compare is true and 0 otherwise. The RTU reads the result as a 1-bit flag
* `req_fmt` is ignored
* Latency: 1 cycle (assumed). The ALU accepts a new request every cycle
