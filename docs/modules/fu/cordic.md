# `cordic` — CORDIC Unit

## Overview

This module is a fixed-point CORDIC Unit supporting division, square roots, reciprocals,and trigonometric functions. It uses a LUT stored in SRAM, so it requires a read request/response channel with SRAM unlike the other FUs.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `DATA_WIDTH`  |     16      | SRAM data width            |
| `WLEN`  |     16      | Word length              |
| `ITER`  |     `WLEN`      | Number of CORDIC iterations             |
| `Q_INT`       |     8      | Integer bits in fixed point format    |
| `Q_FRAC`      |     8      | Fractional bits in fixed point format |
| `ADDR_WIDTH`  |     9      | SRAM address width |
| `LUT_BASE`  |     `9'h000`      | Base SRAM address of the CORDIC LUT |

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
| `sram_rd_if`  | SRAM read request and response channel to the SRAM |

## Architecture Overview