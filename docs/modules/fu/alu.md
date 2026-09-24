---
description: "Fixed-point ALU supporting addition, subtraction, and comparison."
---

# `alu` — Fixed-point ALU

## Overview

This module is a fixed-point ALU supporting addition, subtraction, and comparison operations.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `WLEN`  |     16      | Word length              |
| `Q_INT`       |     8      | Integer bits in fixed point format    |
| `Q_FRAC`      |     8      | Fractional bits in fixed point format |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |
| `fu`  |     [`fu_if.server`](../tinytracer_if.md#fu_if)      | Micro-op request and response channel from FU Control |

## Architecture Overview