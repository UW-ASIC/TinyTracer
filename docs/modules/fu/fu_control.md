# `fu_control` — Instantiates functional units

## Overview

This module is a top-level wrapper that instantiates the 4 functional units (ALU, CORDIC, Multiplier, and RNG).

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `ADDR_WIDTH`  |     9      | SRAM address width             |
| `WLEN`  |     16      | Word length              |
| `MICRO_W`  |     13    | Micro operation width             |
| `DATA_WIDTH`  |     16      | SRAM data width |
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
| `reg_file_if`  | Register file read/write port |
| `micro_if`  | Micro-op request and response channel from the Decode Unit |
| `sram_rd_if`  | SRAM read request and response channel to the SRAM for CORDIC LUT |

## Architecture Overview