# `io` — Communicates with external device to load scenes and render pixels

## Overview

This module instantiates the UART submodule and translates UART frames to control and data signals for SRAM to initialize scene objects. This module also decomposes pixel colour data into UART frames to send to the host device.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `ADDR_WIDTH`  |     8      | SRAM address width              |
| `DATA_WIDTH`  |     16      | SRAM data width              |
| `COLOUR_DEPTH`  |     8      | Bits per colour channel             |
| `RENDER_START`  |     `8'h00`      | RENDER message start byte |
| `OBJ_START`  |     `8'h01`      | OBJECT message start byte |
| `PIXEL_START`  |     `8'h00`      | PIXEL message start byte |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |
| `uart_rx`  |     1      | UART serial input from the host device |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `uart_tx`  |     1      | UART serial output to the host device |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| `colour_if`  | Pixel colour stream from the Accumulator |
| `sram_wr_if`  | SRAM write request channel |
| `render_if`  | Render strobe and image dimensions to the RTU |

## Architecture Overview