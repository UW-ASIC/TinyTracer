---
description: "Wrapper for TinyTracer's 512 x 16 scene SRAM, with a behavioural model for simulation."
---

# `scene_sram` — Scene SRAM

## Overview

This module is the single-port SRAM that holds the scene: 512 words of 16 bits (see [Scene Encoding](../../encoding/scene.md)). The [SRAM Controller](sram_control.md) drives it. The module wraps the SRAM so that the rest of the design does not depend on which memory is used.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `ADDR_WIDTH`  |     9      | Width of SRAM addresses               |
| `DATA_WIDTH`  |     16     | Width of SRAM data words              |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `wen`  |     1      | Write `din` to `addr` at the rising clock edge |
| `addr`  |     `ADDR_WIDTH`      | Address to read or write |
| `din`  |     `DATA_WIDTH`      | Write data |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `dout`  |     `DATA_WIDTH`      | Word at `addr`, read at the previous rising clock edge |

## Architecture Overview

- __Simulation__: a behavioural model. At each rising clock edge, it writes `din` to `addr` if `wen` is high, and loads the word at `addr` into `dout`. A read of the address being written returns the old word
- __Synthesis__ (`SYNTHESIS` defined, as Yosys does): the SRAM macro will be instantiated here. IHP's `RM_IHPSG13_1P_512x16_c2_bm_bist` fits, but it is not integrated into the flow yet. Until then, `dout` is tied to 0 so that the flow does not build the memory out of flip-flops
