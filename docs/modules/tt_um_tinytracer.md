# `tt_um_tinytracer` — Top-Level Module for TinyTracer

## Overview

This module instantiates the SRAM, RTU, Accumulator, Decode Unit, FU Control Unit, Register File, and I/O Unit.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `ADDR_WIDTH`  |     9      | Width of SRAM addresses               |
| `DATA_WIDTH`  |     16     | Width of SRAM data words              |
| `BANK_WIDTH`  |     4      | Width of SRAM bank address            |
| `FCLK`        | 50,000,000 | Clock frequency                       |
| `BAUD`        |  115,200   | UART baud rate                        |
| `IMG_W`       |     64     | Output image width                    |
| `IMG_H`       |     64     | Output image height                   |
| `SPP`         |     8      | Samples per pixel                     |
| `MAX_BOUNCES` |     10     | Ray bounce limit                      |
| `COLOUR_DEPTH` |     8      | Bits per colour channel           |
| `Q_INT`       |     8      | Integer bits in fixed point format    |
| `Q_FRAC`      |     8      | Fractional bits in fixed point format |
| `ITER`        |     TBD         | Number of CORDIC iterations           |
| `MACRO_W`     |    101     | Width of macro-op encoding            |
| `WLEN`        |     16     | Word length                           |

## Interface

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal               |
| `rst_n`  |     1     | Active-low reset              |
| `uart_rx`  |     1     | Receives scene data sent from host device to load into SRAM |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `uart_tx`  |     1      | Streams coloured pixel data back to host device              |