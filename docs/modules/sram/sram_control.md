# `sram_control` — SRAM Controller

## Overview

This module selects a request from the I/O Unit, RTU, or CORDIC request channel and responds with the appropriate data. This module also maps input addresses to appropriate SRAM control signals for reads and writes.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `ADDR_WIDTH`  |     9      | Width of SRAM addresses               |
| `DATA_WIDTH`  |     16     | Width of SRAM data words              |
| `BANK_WIDTH`  |     4      | Width of SRAM bank address            |
| `WLEN`        |     16     | Word length                           |

## Interface

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal               |
| `rst_n`  |     1     | Active-low reset              |
| `io_sram_req_valid`  |     1      | IO write request valid            |
| `io_sram_req_wen`        |     1     | Write enable signal            |
| `io_sram_req_addr`        |     `ADDR_WIDTH`     | Write address            |
| `io_sram_req_wdata`        |     `DATA_WIDTH`     | Write data            |
| `rtu_sram_req_valid`  |     1      | RTU read request valid            |
| `rtu_sram_req_raddr`        |     `ADDR_WIDTH`     | Read address            |
| `rtu_sram_resp_ready`        |     `ADDR_WIDTH`     | RTU ready to accept SRAM data            |
| `cordic_sram_req_valid`        |     1     | CORDIC read request valid          |
| `cordic_sram_req_raddr`  |     `ADDR_WIDTH`     | Read address           |
| `cordic_sram_resp_ready`        |     1     | CORDIC ready to accept SRAM data            |
| `dout`        |     `DATA_WIDTH`     | Output data from SRAM           |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `io_sram_req_ready`  |     1      | IO write request can be accepted               |
| `rst_n`  |     1     | Active-low reset              |
| `io_sram_req_valid`  |     1      | IO write request valid            |
| `io_sram_req_wen`        |     1     | Write enable signal            |
| `io_sram_req_addr`        |     `ADDR_WIDTH`     | Write address            |
| `io_sram_req_wdata`        |     `DATA_WIDTH`     | Write data            |
| `rtu_sram_req_ready`        |     1     | RTU read request can be accepted            |
| `rtu_sram_resp_valid`        |     1     | RTU read data valid            |
| `rtu_sram_resp_rdata`        |     `DATA_WIDTH`     | Read data            |
| `cordic_sram_req_ready`        |     1     | CORDIC read request can be accepted         |
| `cordic_sram_resp_valid`        |     1     | CORDIC read data valid           |
| `cordic_sram_resp_rdata`        |     `DATA_WIDTH`     | Read data        |
| `wen`        |     1     | SRAM write enable           |
| `bank_sel`        |     `BANK_WIDTH`     | SRAM bank selector            |
| `addr`        |     `ADDR_WIDTH`-`BANK_WIDTH`     | SRAM address for reads/writes           |
| `din`        |     `DATA_WIDTH`     | SRAM input data           |

## Architecture Overview