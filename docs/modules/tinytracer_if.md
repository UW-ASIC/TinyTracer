---
description: "SystemVerilog interfaces that connect TinyTracer's modules, with their signals and modports."
---

# `tinytracer_if` — Interfaces between TinyTracer modules

## Overview

TinyTracer's modules talk to each other through the SystemVerilog interfaces defined in `src/tinytracer_if.sv`. Each interface bundles the signals of one channel and has two modports, one for each end of the channel. Each module doc lists its interface ports in an Interfaces section as `interface.modport`, e.g. `macro_if.client`.

Most channels use a valid/ready handshake: a transfer happens on a cycle where both `valid` and `ready` are high.

In the signal tables below, Direction is from the point of view of the `client` or `src` modport. The `server` or `sink` modport has every direction reversed.

## `stream_if`

Generic valid/ready stream carrying a `W`-bit payload. Carries UART bytes between the I/O Unit and the UART.

### Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `W`  |     8      | Payload width |

### Signals

| Name          |   Width    | Direction | Description                           |
|---------------|:------------:|:------------:|---------------------------------------|
| `valid`  |     1      | output | `data` is valid |
| `data`  |     `W`      | output | Payload |
| `ready`  |     1      | input | Sink can accept `data` |

### Modports

| Modport          | Used by                           |
|---------------|---------------------------------------|
| `src`  | [`uart`](io/uart.md) (`rx`) |
| `sink`  | [`uart`](io/uart.md) (`tx`) |

## `colour_if`

Valid/ready stream carrying one RGB colour. Carries sample colours from the RTU to the Accumulator, and pixel colours from the Accumulator to the I/O Unit.

### Signals

| Name          |   Width    | Direction | Description                           |
|---------------|:------------:|:------------:|---------------------------------------|
| `valid`  |     1      | output | `colour` is valid |
| `colour`  |     `rgb_t`      | output | RGB colour, `COLOUR_DEPTH` bits per channel |
| `ready`  |     1      | input | Sink can accept `colour` |

### Modports

| Modport          | Used by                           |
|---------------|---------------------------------------|
| `src`  | [`rtu`](rtu/rtu.md), [`shader_core`](rtu/shader_core.md), [`accumulator`](accumulator/accumulator.md) (`pixel`) |
| `sink`  | [`accumulator`](accumulator/accumulator.md) (`sample`), [`io`](io/io.md) |

## `macro_if`

RTU to Decode Unit channel. The RTU sends a macro-op request and the Decode Unit responds with a vector result. See [Instruction Encoding](../encoding/instruction.md) for the macro-op format.

### Signals

| Name          |   Width    | Direction | Description                           |
|---------------|:------------:|:------------:|---------------------------------------|
| `req_valid`  |     1      | output | Macro-op request is valid |
| `req_op`  |     `macro_word_t`      | output | Macro-op (`MACRO_W` bits) |
| `req_ready`  |     1      | input | Decode Unit can accept a macro-op |
| `resp_valid`  |     1      | input | Macro-op result is valid |
| `resp_result`  |     `vec3_t`      | input | Macro-op result (scalar results in `x`) |
| `resp_ready`  |     1      | output | Client can accept the result |

### Modports

| Modport          | Used by                           |
|---------------|---------------------------------------|
| `client`  | [`rtu`](rtu/rtu.md), [`ray_generator`](rtu/ray_gen/ray_generator.md), [`intersection_unit`](rtu/intersection_unit.md), [`shader_core`](rtu/shader_core.md) |
| `server`  | [`decode`](decode/decode.md) |

## `micro_if`

Decode Unit to FU Control channel. The Decode Unit issues a micro-op request and FU Control strobes `resp_done` when a micro-op completes. Results are written to the register file, not returned over this channel.

### Signals

| Name          |   Width    | Direction | Description                           |
|---------------|:------------:|:------------:|---------------------------------------|
| `req_valid`  |     1      | output | Micro-op request is valid |
| `req_op`  |     `micro_word_t`      | output | Micro-op (`MICRO_W` bits) |
| `req_ready`  |     1      | input | FU Control can accept a micro-op |
| `resp_done`  |     1      | input | One micro-op has completed |

### Modports

| Modport          | Used by                           |
|---------------|---------------------------------------|
| `client`  | [`decode`](decode/decode.md) |
| `server`  | [`fu_control`](fu/fu_control.md) |

## `fu_if`

FU Control to one functional unit channel. `req_opcode` is an `alu_op_t` for the ALU and a `cordic_op_t` for CORDIC; the multiplier ignores it.

### Signals

| Name          |   Width    | Direction | Description                           |
|---------------|:------------:|:------------:|---------------------------------------|
| `req_valid`  |     1      | output | Request is valid |
| `req_op1`  |     `WLEN`      | output | First operand |
| `req_op2`  |     `WLEN`      | output | Second operand |
| `req_opcode`  |     3      | output | Functional unit opcode |
| `req_ready`  |     1      | input | Functional unit can accept a request |
| `resp_done`  |     1      | input | `resp_result` is valid |
| `resp_result`  |     `WLEN`      | input | Result |

### Modports

| Modport          | Used by                           |
|---------------|---------------------------------------|
| `client`  | [`fu_control`](fu/fu_control.md) |
| `server`  | [`alu`](fu/alu.md), [`cordic`](fu/cordic.md), [`multiplier`](fu/multiplier.md) |

## `sram_rd_if`

Read channel into the SRAM controller, used by the RTU.

### Signals

| Name          |   Width    | Direction | Description                           |
|---------------|:------------:|:------------:|---------------------------------------|
| `req_valid`  |     1      | output | Read request is valid |
| `req_raddr`  |     `ADDR_WIDTH`      | output | Read address |
| `req_ready`  |     1      | input | SRAM controller can accept a read request |
| `resp_valid`  |     1      | input | `resp_rdata` is valid |
| `resp_rdata`  |     `DATA_WIDTH`      | input | Read data |
| `resp_ready`  |     1      | output | Client can accept the read data |

### Modports

| Modport          | Used by                           |
|---------------|---------------------------------------|
| `client`  | [`rtu`](rtu/rtu.md) |
| `server`  | [`sram_control`](sram/sram_control.md) (`rtu_rd`) |

## `sram_wr_if`

Write channel into the SRAM controller, used by the I/O Unit.

### Signals

| Name          |   Width    | Direction | Description                           |
|---------------|:------------:|:------------:|---------------------------------------|
| `req_valid`  |     1      | output | Write request is valid |
| `req_wen`  |     1      | output | Write enable |
| `req_waddr`  |     `ADDR_WIDTH`      | output | Write address |
| `req_wdata`  |     `DATA_WIDTH`      | output | Write data |
| `req_ready`  |     1      | input | SRAM controller can accept a write request |

### Modports

| Modport          | Used by                           |
|---------------|---------------------------------------|
| `client`  | [`io`](io/io.md) |
| `server`  | [`sram_control`](sram/sram_control.md) (`io_wr`) |

## `render_if`

I/O Unit to RTU channel carrying a one-cycle render strobe and the image dimensions. `img_w` and `img_h` are each two RENDER message bytes, and the I/O Unit holds them until the next RENDER message. See [UART Frame Encoding](../encoding/uart_frame.md).

### Signals

| Name          |   Width    | Direction | Description                           |
|---------------|:------------:|:------------:|---------------------------------------|
| `render`  |     1      | output | One-cycle strobe to start rendering |
| `img_w`  |     `DIM_WIDTH`      | output | Image width |
| `img_h`  |     `DIM_WIDTH`      | output | Image height |

### Modports

| Modport          | Used by                           |
|---------------|---------------------------------------|
| `src`  | [`io`](io/io.md) |
| `sink`  | [`rtu`](rtu/rtu.md) |
