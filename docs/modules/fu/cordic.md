---
description: "Fixed-point CORDIC unit for division, square roots, reciprocals, and trigonometric functions."
---

# `cordic` — CORDIC Unit

## Overview

This module is a fixed-point CORDIC Unit supporting division, square roots, reciprocals, and trigonometric functions. Its LUT is held in a ROM local to the module, so like the other FUs it only communicates with FU Control.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `WLEN`  |     16      | Word length              |
| `ITER`  |     `WLEN`      | Number of CORDIC iterations             |
| `Q_INT`       |     8      | Integer bits in fixed point format    |
| `Q_FRAC`      |     8      | Fractional bits in fixed point format |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| `fu_if`  | Micro-op request and response channel from FU Control |

## Architecture Overview