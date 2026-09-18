# `uart` — UART frame parser

## Overview

This module parses UART messages sent from the host device, processing input commands for scene initialization and rendering. The UART module also converts pixel colour data into UART frames to transmit back to the host.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `FCLK`  |     25,000,000      | Clock frequency             |
| `BAUD`  |     115,200      | UART baud rate              |

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
| `stream_if`  | Byte stream from host device to send to the I/O Unit |
| `stream_if`  | Byte stream from I/O Unit to send to host device |

## Architecture Overview