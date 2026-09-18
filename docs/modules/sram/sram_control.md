# `sram_control` — SRAM Controller

## Overview

This module selects a request from the I/O Unit, RTU, or CORDIC request channel and responds with the appropriate data. This module also maps input addresses to appropriate SRAM control signals for reads and writes.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `ADDR_WIDTH`  |     9      | Width of SRAM addresses               |
| `DATA_WIDTH`  |     16     | Width of SRAM data words              |
| `BANK_WIDTH`  |     4      | Width of SRAM bank address            |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |
| `dout`  |     `DATA_WIDTH`      | Output data from SRAM |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `wen`  |     1      | SRAM write enable |
| `bank_sel`  |     1      | SRAM bank select enable |
| `addr`  |     `ADDR_WIDTH`-`BANK_WIDTH`      | SRAM address for reads/writes |
| `din`  |     `DATA_WIDTH`      | SRAM input data |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| `sram_wr_if`  | SRAM write request channel from the I/O Unit |
| `sram_rd_if`  | SRAM read request and response channel from the RTU |
| `sram_rd_if`  | SRAM read request and response channel from CORDIC |

## Architecture Overview