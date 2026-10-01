---
description: "Register file holding macro-op operands and micro-op results, with a parallel load and result output for the Decode Unit and one write port and two read ports for FU Control."
---

# `reg_file` — Register file for the FUs

## Overview

This module stores the operands of the current macro-op and the intermediate results of its micro-ops. The Decode Unit loads all of a macro-op's operands in a single cycle and reads the macro-op result directly from R0-R2, so it never addresses individual registers. FU Control uses one write port and two read ports so that a micro-op can read both of its source registers in the same cycle that another micro-op writes its result.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `WLEN`  |     16      | Word length              |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |
| `load`  |     1      | Parallel load enable |
| `load_u`  |     `vec3_t`      | Operand $\mathbf{\vec{u}}$, loaded into R0-R2 |
| `load_v`  |     `vec3_t`      | Operand $\mathbf{\vec{v}}$, loaded into R3-R5 |
| `wen`  |     1      | Write port enable |
| `waddr`  |     3      | Write port register address |
| `wdata`  |     `WLEN`      | Write port data |
| `raddr1`  |     3      | Read port 1 register address |
| `raddr2`  |     3      | Read port 2 register address |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `result`  |     `vec3_t`      | Macro-op result, `{R2, R1, R0}` |
| `rdata1`  |     `WLEN`      | Read port 1 data |
| `rdata2`  |     `WLEN`      | Read port 2 data |

## Architecture Overview

The register file holds eight `WLEN`-bit registers, R0 to R7, in flip-flops. Micro-ops address them through the 3-bit `RD`, `RS1`, and `RS2` fields defined in [Instruction Encoding](../../encoding/instruction.md).

- __Parallel load__: on the rising clock edge, when `load` is high, the macro-op operands are written in one cycle: R0, R1, R2 $\leftarrow$ $u_1$, $u_2$, $u_3$ and R3, R4, R5 $\leftarrow$ $v_1$, $v_2$, $v_3$ (`load_u.x`, `load_u.y`, `load_u.z`, `load_v.x`, `load_v.y`, `load_v.z`). R6 and R7 are unchanged. Every macro-op uses this layout, so no per-macro-op operand mapping is needed.
- __Result__: `result` is a combinational read of R0-R2, with `result.x` = R0, `result.y` = R1, and `result.z` = R2. Scalar results are in R0 (`result.x`).
- __Write port__: on the rising clock edge, `wdata` is written to register `waddr` when `wen` is high.
- __Read ports__: `rdata1` and `rdata2` are combinational reads of registers `raddr1` and `raddr2`. The two ports are independent and may address the same register.
- __Read-during-write__: there is no bypass from the write port to the read ports. A value written on a clock edge is visible on the read ports from the following cycle, and reading the register being written in the same cycle returns the old value. We will include a debug signal for this equation, but the FU control and decoder should avoid this case.
- __Load and write in the same cycle__: this cannot happen, since the Decode Unit only loads while no micro-ops are in flight. If it did, `load` takes priority.
- __Reset__: all registers are cleared to zero.

The Decode Unit uses the parallel load and `result`; FU Control uses the write port and both read ports. The two never access the register file at the same time: the Decode Unit loads operands in the cycle it accepts a macro-op, before any micro-op reads or writes a register, and reads `result` in `WRITEBACK`, after every micro-op has completed. A scalar macro-op's micro-op issues in the same cycle as the load, but it takes its operands from the request rather than the read ports, and its result is written to R0 at least one cycle later.
