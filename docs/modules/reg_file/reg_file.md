# `reg_file` — Register file for the FUs

## Overview

This module is used to store initial data for micro-ops to operate on as well as intermediate results from micro-ops. It has one write port and two read ports so that a micro-op can read both of its source registers in the same cycle that another micro-op writes its result.

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
| `wen`  |     1      | Write port enable |
| `waddr`  |     3      | Write port register address |
| `wdata`  |     `WLEN`      | Write port data |
| `raddr1`  |     3      | Read port 1 register address |
| `raddr2`  |     3      | Read port 2 register address |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `rdata1`  |     `WLEN`      | Read port 1 data |
| `rdata2`  |     `WLEN`      | Read port 2 data |

## Architecture Overview

The register file holds eight `WLEN`-bit registers, R0 to R7, in flip-flops. Micro-ops address them through the 3-bit `RD`, `RS1`, and `RS2` fields defined in [Instruction Encoding](../../encoding/instruction.md).

- __Write port__: on the rising clock edge, `wdata` is written to register `waddr` when `wen` is high.
- __Read ports__: `rdata1` and `rdata2` are combinational reads of registers `raddr1` and `raddr2`. The two ports are independent and may address the same register.
- __Read-during-write__: there is no bypass from the write port to the read ports. A value written on a clock edge is visible on the read ports from the following cycle, and reading the register being written in the same cycle returns the old value.
- __Reset__: all registers are cleared to zero.

The Decode Unit and FU Control are the two masters of the register file. The Decode Unit uses the write port to initialize operands and read port 1 to read macro-op results. FU Control uses both read ports to fetch micro-op operands and the write port to write micro-op results. Only one master drives the ports at a time, since the Decode Unit only accesses the register file while no micro-ops are in flight.