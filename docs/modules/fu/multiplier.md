# `multiplier` — Fixed-point multiplier

## Overview

This module is a fixed-point multiplier using the TBD algorithm (replace TBD with implemented algorithm later).

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

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| `fu_if`  | Micro-op request and response channel from FU Control |

## Architecture Overview