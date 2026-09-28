---
description: "UART transceiver that sends and receives bytes to communicate with the Host."
---

# `uart` — UART transceiver

## Overview

This module parses UART bytes sent from the host device, producing a stream of bytes to be processed. The UART module also sends bytes back to the host according to the UART frame semantics, used to return pixel data.

This module only sends and receives bytes, processing of those bytes will be performed in the IO block.

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |
| `clk_q`  | 1  | Divided clock for UART transmission - is at 16x baud rate |
| `uart_rx`  |     1      | UART serial input from the host device |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `uart_tx`  |     1      | UART serial output to the host device |

### Interfaces

|Name | Type          | Description                           |
|-----|---------------|---------------------------------------|
|`byte_in`| [`stream_if.sink`](../tinytracer_if.md#stream_if)  | UART byte input from IO block |
|`byte_out`| [`stream_if.src`](../tinytracer_if.md#stream_if)  | UART byte output to IO block |

## Architecture Overview
Reading: https://zbotic.in/uart-communication-baud-rate-tx-rx-and-how-it-works/

Every UART byte transmitted or received is preceeded by one start bit, and one stop bit.
To sample data on the Rx side, the average of 16 bit-samples is used. We start counting intervals when we notice the Rx line go low, starting the start bit (the lines idle high).
To tradeoff sampling logic vs accuracy, we will sample on intervals 6, 8, and 10, then take the majority vote.
If the start bit is not 0, discard the frame and go back to looking for a falling edge.
Discard data also if the stop bit is not 1.

This is a complete UART byte-frame:

| IDLE | START | D0 | D1 | D2 | D3 | D4 | D5 | D6 | D7 | STOP |
|:----:|:-----:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:----:|
| HIGH | LOW   |data|bit |by  |bit |(LSB|first)|cont..|...| HIGH |

Transmitting is much more simple; frame bytes with start & stop, then shift the 10-bit stream out, on every 16th `clk_q` pulse.

The UART will have a CDC for the rx wire, as it is received from the IO pins.

### Backpressure
If the UART's outgoing shift register is full, it should assert `byte_in.ready = 0`.
Data should be loaded from `byte_in.data` into the shift register when both `byte_in.ready` && `byte_in.valid`.
When the UART's incoming shift register is full, it should first strip start/stop bits if the frame is valid and move it to an intermediate holding register (which is `byte_out.data` or assigned to it), then assert `byte_out.valid`.
If the start/stop bits do not match, the byte should be discarded.
Data should be rendered invalid after it is consumed (`byte_out.ready` && `byte_out.valid`).
We assume our chip will be fast enough to not backpressure byte_out, but it is good practice to implement it.

## UArch Diagram

![IO Uarch Diagram](../../svg/uwasic_tt_io_uarch.svg)