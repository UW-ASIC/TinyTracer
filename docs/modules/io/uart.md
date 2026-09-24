---
description: "UART transceiver that parses scene and render commands from the host and transmits pixel colour frames back."
---

# `uart` — UART frame parser

## Overview

This module parses UART messages sent from the host device, processing input commands for scene initialization and rendering. The UART module also converts pixel colour data into UART frames to transmit back to the host.

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |
| `clk_q`  | 1  | Divided clock for UART transmission - is at 16x baud rate |
| `uart_rx`  |     1      | UART serial input from the host device |
| `tx`  |     [`stream_if.sink`](../tinytracer_if.md#stream_if)      | UART byte input from IO block |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `uart_tx`  |     1      | UART serial output to the host device |
| `rx`  |     [`stream_if.src`](../tinytracer_if.md#stream_if)      | UART byte output to IO block |

## Architecture Overview
Reading: https://zbotic.in/uart-communication-baud-rate-tx-rx-and-how-it-works/

Every UART byte transmitted or received is preceeded by one start bit, and one stop bit.
To sample data on the Rx side, the average of 16 bit-samples is used. We start counting intervals when we notice the Rx line go low, starting the start bit (the lines idle high).
To tradeoff sampling logic vs accuracy, we will sample on intervals 6, 8, and 10, then take the majority vote.
If the start bit is not 0, discard the frame and go back to looking for a falling edge.
Discard data also if the stop bit is not 1.

This is a complete UART byte-frame:
| IDLE | START | D0 | D1 | D2 | D3 | D4 | D5 | D6 | D7 | STOP |
|------|-------|----|----|----|----|----|----|----|----|------|
| HIGH | LOW   |data|bit |by  |bit |(LSB|first)|cont..|...| HIGH |

Transmitting is much more simple; frame bytes with start & stop, then shift the 10-bit stream out, on every 16th `clk_q` pulse.

The UART will have a CDC for the rx wire, as it is received from the IO pins.

### Backpressure
If the UART's outgoing shift register is full, it should assert `uart_in.ready = 0`.
Data should be loaded from `uart_in.data` into the shift register when both `uart_in.ready` && `uart_in.valid`.
When the UART's incoming shift register is full, it should first move it to an intermediate holding register (which is `uart_out.data` or assigned to it), then assert `uart_out.valid`.
Data should be rendered invalid after it is consumed (`uart_out.ready` && `uart_out.valid`).
We assume our chip will be fast enough to not backpressure uart_out, but it is good practice to implement it.