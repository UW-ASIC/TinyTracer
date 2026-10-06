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

Valid/ready stream carrying one RGB colour. Carries sample colours from the RTU to the Accumulator (`W` = `SAMPLE_DEPTH`), and pixel colours from the Accumulator to the I/O Unit (`W` = `COLOUR_DEPTH`).

### Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `W`  |     `COLOUR_DEPTH` (8)      | Bits per colour channel: `SAMPLE_DEPTH` (12) for samples, `COLOUR_DEPTH` (8) for pixels |

### Signals

| Name          |   Width    | Direction | Description                           |
|---------------|:------------:|:------------:|---------------------------------------|
| `valid`  |     1      | output | `colour` is valid |
| `colour`  |     3 $\times$ `W`      | output | RGB colour, `W` bits per channel, `{r, g, b}` |
| `ready`  |     1      | input | Sink can accept `colour` |

### Modports

| Modport          | Used by                           |
|---------------|---------------------------------------|
| `src`  | [`rtu`](rtu/rtu.md), [`shader_core`](rtu/shader_core.md), [`accumulator`](accumulator/accumulator.md) (`pixel`) |
| `sink`  | [`accumulator`](accumulator/accumulator.md) (`sample`), [`io`](io/io.md) |

## `macro_if`

RTU to Execution Unit channel. The RTU sends a macro-op request from its request register and the EXU responds with a vector result. The EXU passes the channel through to the Decode Unit, so both use the `server` modport. See [Instruction Encoding](../encoding/instruction.md) for the macro-op format.

### Signals

| Name          |   Width    | Direction | Description                           |
|---------------|:------------:|:------------:|---------------------------------------|
| `req_valid`  |     1      | output | Macro-op request is valid |
| `req_op`  |     `macro_word_t`      | output | Macro-op (`MACRO_W` bits, including `FMT`) |
| `req_ready`  |     1      | input | EXU can accept a macro-op |
| `resp_valid`  |     1      | input | Macro-op result is valid |
| `resp_result`  |     `vec3_t`      | input | Macro-op result, register file R0-R2 (scalar results and compare flags in `x`) |
| `resp_ready`  |     1      | output | Client can accept the result |

### Modports

| Modport          | Used by                           |
|---------------|---------------------------------------|
| `client`  | [`rtu`](rtu/rtu.md) |
| `server`  | [`exu`](exu/exu.md), [`decode`](exu/decode.md) |

## `rtu_req_if`

RTU sub-block to RTU request path channel. The active sub-block writes fields of the RTU's shared request register and sends it to the EXU as a macro-op, and the RTU returns the response to it. See [Handshakes](rtu/rtu.md#handshakes) for the timing. The Ray Generator drives the operand values on `req_u` and `req_v`. The Intersection Unit's and Shader Core's operand selects, and the size shift and sign flip controls, are not defined yet.

### Signals

| Name          |   Width    | Direction | Description                           |
|---------------|:------------:|:------------:|---------------------------------------|
| `req_we`  |     8      | output | Request register field write enables, `{FMT, u3, u2, u1, v3, v2, v1, MACROOP}` |
| `req_fmt`  |     `fmt_t`      | output | Value written to `FMT` when `req_we[7]` is high |
| `req_u`  |     `vec3_t`      | output | Values written to $u_3$, $u_2$, $u_1$ (`z`, `y`, `x`) when `req_we[6:4]` are high |
| `req_v`  |     `vec3_t`      | output | Values written to $v_3$, $v_2$, $v_1$ (`z`, `y`, `x`) when `req_we[3:1]` are high |
| `req_resize`  |     1      | output | Apply the resize pre-shift to `req_u` before it is written (see [Number Formats](../encoding/number_format.md#resize-pre-shift)) |
| `req_op`  |     `macro_op_t`      | output | Value written to `MACROOP` when `req_we[0]` is high |
| `req_valid`  |     1      | output | Send the request register (with this cycle's writes) as a macro-op |
| `req_ready`  |     1      | input | The EXU can accept a macro-op (`macro.req_ready`) |
| `resp_valid`  |     1      | input | One-cycle pulse: the macro-op response is on `resp_result` |
| `resp_flag`  |     1      | input | Compare flag, bit 0 of `resp_result.x` |
| `resp_result`  |     `vec3_t`      | input | Macro-op result |

### Modports

| Modport          | Used by                           |
|---------------|---------------------------------------|
| `client`  | [`ray_generator`](rtu/ray_gen/ray_generator.md), [`intersection_unit`](rtu/intersection_unit.md), [`shader_core`](rtu/shader_core.md) |
| `server`  | [`rtu`](rtu/rtu.md) |

## `micro_if`

Decode Unit to FU Control channel. The Decode Unit issues a micro-op request and FU Control strobes `resp_done` when a micro-op completes. Results are written to the register file, not returned over this channel. For scalar macro-ops, the operands travel on this channel instead of being read from the register file.

### Signals

| Name          |   Width    | Direction | Description                           |
|---------------|:------------:|:------------:|---------------------------------------|
| `req_valid`  |     1      | output | Micro-op request is valid |
| `req_op`  |     `micro_word_t`      | output | Micro-op (`MICRO_W` bits) |
| `req_fmt`  |     `fmt_t`      | output | `FMT` bit of the macro-op: multiply shift and square root mode |
| `req_direct`  |     1      | output | Use `req_u1` and `req_v1` as operands instead of registers `RS1` and `RS2` (scalar macro-ops) |
| `req_u1`  |     `WLEN`      | output | First operand when `req_direct` is high ($u_1$ of the request) |
| `req_v1`  |     `WLEN`      | output | Second operand when `req_direct` is high ($v_1$ of the request) |
| `req_ready`  |     1      | input | FU Control can accept a micro-op |
| `resp_done`  |     1      | input | One micro-op has completed |

### Modports

| Modport          | Used by                           |
|---------------|---------------------------------------|
| `client`  | [`decode`](exu/decode.md) |
| `server`  | [`fu_control`](exu/functional_units/fu_control.md) |

## `fu_if`

FU Control to one functional unit channel. `req_opcode` is an `alu_op_t` for the ALU and a `cordic_op_t` (in `req_opcode[1:0]`) for CORDIC; the multiplier ignores it. For the CORDIC unit, `req_op1` is its operand $A$ and `req_op2` its operand $B$. `req_fmt` selects the multiplier's product shift and the CORDIC square root mode; the ALU ignores it.

### Signals

| Name          |   Width    | Direction | Description                           |
|---------------|:------------:|:------------:|---------------------------------------|
| `req_valid`  |     1      | output | Request is valid |
| `req_op1`  |     `WLEN`      | output | First operand |
| `req_op2`  |     `WLEN`      | output | Second operand |
| `req_opcode`  |     3      | output | Functional unit opcode |
| `req_fmt`  |     `fmt_t`      | output | Number format select (see [Number Formats](../encoding/number_format.md)) |
| `req_ready`  |     1      | input | Functional unit can accept a request |
| `resp_done`  |     1      | input | `resp_result` is valid |
| `resp_result`  |     `WLEN`      | input | Result |

### Modports

| Modport          | Used by                           |
|---------------|---------------------------------------|
| `client`  | [`fu_control`](exu/functional_units/fu_control.md) |
| `server`  | [`alu`](exu/functional_units/alu.md), [`cordic`](exu/functional_units/cordic.md), [`multiplier`](exu/functional_units/multiplier.md) |

## `sram_rd_if`

Read channel into the SRAM controller, used by the RTU. `ADDR_WIDTH` is 9 (512 words).

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
| `client`  | [`rtu`](rtu/rtu.md), [`intersection_unit`](rtu/intersection_unit.md) |
| `server`  | [`sram_control`](sram/sram_control.md) (`rtu_rd`) |

## `sram_wr_if`

Write channel into the SRAM controller, used by the I/O Unit. `ADDR_WIDTH` is 9 (512 words).

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

I/O Unit to RTU channel carrying a one-cycle render strobe and the image dimensions. `img_w` and `img_h` (`DIM_WIDTH` = 12 bits) each come from two RENDER message bytes, low byte first, with the upper 4 bits of the high byte unused, and the I/O Unit holds them until the next RENDER message. The image must be square, with a width that is a power of 2 and at most 512. See [UART Frame Encoding](../encoding/uart_frame.md).

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
