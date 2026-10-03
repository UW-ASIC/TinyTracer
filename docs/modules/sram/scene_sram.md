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

- __Simulation__: a behavioural model. At each rising clock edge, it writes `din` to `addr` if `wen` is high, and otherwise loads the word at `addr` into `dout`. A write cycle does not read: `dout` keeps its value, as in the macro
- __Synthesis__ (`SYNTHESIS` defined, as Yosys does): IHP's `RM_IHPSG13_1P_512x16_c2_bm_bist` macro, 236.80 × 191.34 µm. Its pins are tied as follows:
    - `A_REN` is `~wen`: with both `A_WEN` and `A_REN` high the macro writes `din` and returns it (write-through)
    - `A_MEN` is 1, so the macro is enabled every cycle
    - `A_DLY` is 1, as the datasheet requires
    - `A_BM` is all ones, so a write covers the whole word
    - the BIST port is unused

### Physical integration

The [IHP SRAM Macro Integration](ihp_sram_macro.md) page has the details, the sources, and what would change for a different macro size.

- __Placement__: the macro sits in the bottom-left corner of the core with orientation FS. Its signal pins are on its bottom edge, so FS turns them up towards the logic. The tile's I/O pins are on the top edge
- __Power__: the Tiny Tapeout SG13CMOS5L tile powers designs with Metal4 stripes only, and the macro blocks Metal2 to Metal4 over its footprint, so the PDN generator stops its stripes at the macro. The `Project.ExtendPowerStripes` step (`librelane_plugin_tinytracer_pdn.py`, running `odb_stripes.py` from [ihp-um-janestreet-prism](https://kdp1965.github.io/ihp-um-janestreet-prism/ihp_sram_macro.html)) redraws them through the macro on its Metal4 supply columns. `VDD!` and `VDDARRAY!` connect to `VPWR`, and `VSS!` to `VGND`
- __Sign-off__:
    - Magic DRC is off and the KLayout DRC of the Tiny Tapeout precheck signs off, because Magic misreads the macro's LEF obstructions
    - LVS treats the macro as a black box
