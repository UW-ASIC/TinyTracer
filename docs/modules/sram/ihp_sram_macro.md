---
description: "How TinyTracer's scene SRAM uses IHP's RM_IHPSG13_1P_512x16_c2_bm_bist macro on the Tiny Tapeout SG13CMOS5L flow, how the RTL uses it, and what changes for a different macro size."
---

# IHP SRAM Macro Integration

## Overview

The scene SRAM (512 words of 16 bits) is IHP's ready-made single-port SRAM macro `RM_IHPSG13_1P_512x16_c2_bm_bist` [7], in the bottom-left corner of TinyTracer's 4x2 tile. The design is hardened with the Tiny Tapeout flow for IHP SG13CMOS5L [8, 9]. This page covers:

- what was changed in the flow to accept the macro, and where each change came from
- how the RTL instantiates and uses the macro
- what would change for a macro of a different size

| Check | Result |
|-------|--------|
| GDS build (`tt-gds-action@ihp-cmos5l`, LibreLane 3.1.0.dev3) | Passes in CI [13] |
| Tiny Tapeout precheck, including the KLayout SG13CMOS5L DRC | Passes in CI [13] |
| Gate-level test, with the SRAM simulated by IHP's behavioural model | Passes in CI [13] |
| LVS (SRAM treated as a black box), routing DRC, antenna | 0 errors (local run) |
| Power grid: OpenROAD `check_power_grid` on the routed design | `VPWR` and `VGND` connected (local run) |

What these checks do not cover yet:

- **Silicon.** No design using these macros on SG13CMOS5L had silicon results when this page was written (October 2026). On sg13g2, Uri Shaked's 1024×8 test chip on TTIHP0p2 has been tested in silicon [6].
- **Timing through the macro.** `sram_control` is still a stub, so there are no timing paths to or from the SRAM yet.
- **Whether the finished logic fits** around the macro.

## The macro and the tile

### The macro

| Property | Value |
|----------|-------|
| Name | `RM_IHPSG13_1P_512x16_c2_bm_bist` (single port, 2:1 column mux, bit mask, BIST port) |
| Size | 236.80 × 191.34 µm, 16.9% of a 4x2 tile |
| Source | IHP-Open-PDK [7], `ihp-sg13cmos5l/libs.ref/sg13cmos5l_sram/` (a link to `ihp-sg13g2/libs.ref/sg13g2_sram/`, so the views are the sg13g2 ones), at the commit that `tt-gds-action@ihp-cmos5l` installs: `2bbec755dc67ca3db0261c3d6163e15735d66710` [8] |
| Signal pins | All on the bottom edge (y = 0 to 0.26 µm), on Metal2 and Metal3 |
| Power pins | Metal4 columns, 2.81 µm wide: `VDD!` (periphery) and `VDDARRAY!` (bit cells) at x = 4.26 + 11.24·k µm, `VSS!` at x = 9.88 + 11.24·k µm. `VDD!` covers y = 0 to 38.8 µm, `VDDARRAY!` y = 45.5 to 191.34 µm, `VSS!` the full height |
| Obstructions | Metal1 to Metal4 over the whole footprint |

### The Tiny Tapeout SG13CMOS5L tile

| Property | Value |
|----------|-------|
| 4x2 die | 854.40 × 313.74 µm. The core starts at (2.88, 3.78) µm, in rows 3.78 µm high [9] |
| Routing layers | Up to Metal4 (`project_top_metal_layer` in tt-support-tools) [9] |
| Power grid | Vertical Metal4 stripes only: pitch 50 µm and width 2.1 µm in the template [10]. The precheck's minimum power-port width is 2.1 µm [9] |
| I/O pins | On the top edge, x ≈ 37 to 190 µm |

The project's top routing layer (Metal4) is the layer the macro blocks and the layer the power grid uses, so:

- nothing can be routed over the macro;
- the tile's power stripes stop at the macro and never reach its supply columns.

The macro's supply columns have to become part of the power grid. That is most of the work below.

## What was done in the flow

All of the flow settings are in the user section of `src/config.json`; the comments there say why each one is set.

| File | Change | Source |
|------|--------|--------|
| `src/config.json` | `MACROS`: the macro, its views from the PDK, its placement | [2], [3] |
| `src/config.json` | `PDN_MACRO_CONNECTIONS`: `VDD!` and `VDDARRAY!` on `VPWR`, `VSS!` on `VGND` | [2], [3], [5] |
| `src/config.json` | `PDN_CFG` and `meta.substituting_steps`: the custom power grid and the `Project.ExtendPowerStripes` step | [2], [3] |
| `src/config.json` | `ERROR_ON_PDN_VIOLATIONS`, `RUN_MAGIC_DRC`, `ERROR_ON_ILLEGAL_OVERLAPS`, `MAGIC_MACRO_STD_CELL_SOURCE`, `MAGIC_EXT_ABSTRACT_CELLS`: sign-off settings | [2], [3], [4], [5] |
| `librelane_plugin_tinytracer_pdn.py` | LibreLane plugin: the `Project.ExtendPowerStripes` step and a fix for netgen's LVS output | Adapted from [2] and [3] |
| `odb_stripes.py` | Draws the power stripes through the macro. Copied unchanged from [2] | [2] |
| `src/pdn_cfg.tcl` | Metal4-only power grid without LibreLane's per-macro grid. Copied from [3] | [3] |
| `src/scene_sram.sv` | Instantiates the macro in synthesis (see [the RTL section](#how-the-rtl-uses-the-macro)) | [5], [6], [7] |
| `test/Makefile` | The gate-level test compiles the macro's behavioural model | [7] |

### Views and placement

- **Views.** `MACROS` points at the macro's GDS, LEF, CDL and Liberty files with `pdk_dir::` paths, so nothing is copied into the repository.
- **Timing corners.** The three Liberty files map to LibreLane's corners: `typ_1p20V_25C`, `fast_1p32V_m55C` and `slow_1p08V_125C`. IHP characterises the fast corner at −55 °C; LibreLane's fast corner is −40 °C.
- **Liberty bug, already fixed at this PDK commit.** Liberty files before IHP-Open-PDK commit `d490cfb2e325` state `max_capacitance` in farads, and OpenROAD then aborts with `RSZ-0169` [5].
- **Placement.** The instance `u_scene_sram.u_sram` is at (3.36, 3.78) µm with orientation FS, the same spot the guide uses [2]:
    - The macro's signal pins are on its bottom edge, so FS (mirrored top to bottom) turns them up towards the free area of the tile.
    - The tile's I/O pins are on its top edge, 118 µm above the macro.

### Power distribution

- **The step.** LibreLane's GeneratePDN leaves the macro unpowered (see [the tile](#the-tiny-tapeout-sg13cmos5l-tile)). `Project.ExtendPowerStripes` runs right after GeneratePDN (`meta.substituting_steps` in `src/config.json`) and runs `odb_stripes.py` [2], which:
    - moves each tile stripe that crosses the macro onto the nearest of the macro's supply columns;
    - adds stripe pairs where a region of the macro (left bit-cell array, the standard-cell band between the arrays, right bit-cell array) has fewer than two VPWR/VGND pairs;
    - redraws those stripes over the full core height;
    - adds Metal1 to Metal4 via stacks where they cross the standard-cell rails outside the macro;
    - leaves one full-height box per stripe, which the Tiny Tapeout pin check needs.
- **Result for this macro.** Five VPWR and five VGND tile stripes moved onto columns, by up to 5.5 µm. One pair was added over the band, so each region has two pairs: six VPWR and six VGND stripes cross the macro.
- **How the plugin loads.** LibreLane imports any module named `librelane_plugin_*` from the Python path. Both the Tiny Tapeout GDS action and a local `tt_tool.py --harden` run LibreLane from the repository root, so the plugin at the root is found without installing anything [2], [3].
- **`src/pdn_cfg.tcl`** [3] is LibreLane's PDN script without its per-macro grid. With a single-layer grid that grid would be empty, and OpenROAD would report PDN-0232/0233.
- **`ERROR_ON_PDN_VIOLATIONS` is off** [3]:
    - GeneratePDN checks the grid before `Project.ExtendPowerStripes` runs, so it always reports the macro as unconnected (179,506 "violations" in our run).
    - OpenROAD's `check_power_grid` passes for `VPWR` and `VGND` on the design that `Project.ExtendPowerStripes` writes, and again on the final routed design.
    - LVS also passes. Re-run those two checks after any change to the macro or its placement (see [Verifying a change](#verifying-a-change)).

### Sign-off settings

These follow the other CMOS5L SRAM projects [2], [3], [4]:

- `RUN_MAGIC_DRC: false` and `ERROR_ON_ILLEGAL_OVERLAPS: false`. The macro's LEF has a Metal4 obstruction bar where `VDD!` ends and `VDDARRAY!` begins (y = 38.8 to 45.5 µm). The redrawn stripes cross it, so Magic reports illegal overlaps there (14 in our run). That bar is not in the macro's GDS [3], [4]. The sign-off DRC is KLayout's SG13CMOS5L deck, which the Tiny Tapeout precheck runs on the real GDS; it passes.
- `MAGIC_MACRO_STD_CELL_SOURCE: "PDK"`: the final layout uses the macro's full GDS [5].
- `MAGIC_EXT_ABSTRACT_CELLS: ["RM_IHPSG13_.*"]`: LVS treats the SRAM as a black box, as the sg13g2 and CMOS5L SRAM projects do [3], [5].
- The plugin also fixes netgen's LVS output: netgen writes the pin names `VDD!`, `VSS!` and `VDDARRAY!` into its JSON with a stray backslash, and LibreLane's LVS step then fails to parse it [3].
- The precheck has accepted the SRAM's marker layers (`SRAM.drawing`, `DigiBnd.drawing`) since tt-support-tools PR #187 [9]. Before that, it rejected them.

### Synthesis

- **Slang frontend.** `src/config.json` sets `USE_SLANG: true`, so LibreLane reads the SystemVerilog with the slang frontend instead of `read_verilog -defer`. The default read cannot resolve the interfaces that `rtu` passes down.
- **No stub module.** LibreLane loads the macro from its Liberty file as a black box, and slang resolves the instance against it, so `src/` needs no stub module for the macro. Tiny Tapeout's port check (`read_verilog -lib`, `hierarchy` without `-check`) accepts the undefined module.
- **Keep attribute.** The instance carries `(* keep *)` (see [Instantiation](#instantiation)).

### CI fixes made along the way

Neither fix is specific to the SRAM, but both jobs had to pass to check it:

- **`.github/workflows/test.yaml`** installs cocotb into a venv. Outside a venv, cocotb 1.9's makefiles export `PYTHONHOME` [12], and Verilator's build then runs the system `/usr/bin/python3` with it and fails with "No module named 'encodings'".
- **`test/Makefile`**: `make clean` no longer loads cocotb's makefiles. The gate-level action runs `make clean` without `GATES=yes`, and with only Icarus installed [8], cocotb's Verilator makefile stopped the job.

### Verifying a change

The full flow can be run locally the same way the GDS action runs it [8], [9]:

1. Set up the tools:
    - a Python 3.11 venv with tt-support-tools' requirements and `librelane==3.1.0.dev3`;
    - tt-support-tools' `ihp-sg13cmos5l` branch cloned into `tt/`;
    - the PDK installed with tt-gds-action's `install_sg13cmos5l.sh`;
    - Docker.
2. Run `./tt/tt_tool.py --create-user-config --ihp`, then `--harden --ihp`, then `--create-tt-submission --ihp`.
3. Run it from a directory outside `/tmp`. The Yosys that tt-support-tools uses (YoWASP) mounts its own temporary directory over `/tmp`, so it cannot see design files there.
4. For a DRC like the precheck's, add `"RUN_KLAYOUT_DRC": true` and `"KLAYOUT_DRC_RUNSET": "pdk_dir::libs.tech/klayout/tech/drc/ihp-sg13cmos5l.drc"` to the local copy of `src/config.json`.
5. Check the power grid with OpenROAD: `read_db` the `.odb` from the `project-extendpowerstripes` step, or from `final/odb`, then `check_power_grid -net VPWR` and `check_power_grid -net VGND`.

## How the RTL uses the macro

### Instantiation

The macro is the instance `u_sram` inside `scene_sram` (`src/scene_sram.sv`), which `tt_um_tinytracer` instantiates as `u_scene_sram`. After synthesis flattens the design, the macro's name is `u_scene_sram.u_sram`. That is the name `MACROS` and `PDN_MACRO_CONNECTIONS` use in `src/config.json`.

`scene_sram` has two implementations, selected by `SYNTHESIS`:

| Build | `SYNTHESIS` | What `scene_sram` contains |
|-------|-------------|----------------------------|
| RTL simulation (Verilator) | Not defined | A behavioural model: an array of 2<sup>`ADDR_WIDTH`</sup> words of `DATA_WIDTH` bits |
| Synthesis (LibreLane's Yosys with slang) | Defined | The macro |
| Gate-level simulation (Icarus) | Not applicable: the netlist contains the macro | IHP's behavioural model of the macro, compiled with `FUNCTIONAL` (`test/Makefile`) |

The instance carries `(* keep *)`. Synthesis removes cells whose outputs nothing reads, and the stub `sram_control` does not read `dout` yet. Once it does, the attribute is harmless.

### Pin connections

| Macro pin | Width | Connected to | Why |
|-----------|-------|--------------|-----|
| `A_CLK` | 1 | `clk` | The design clock |
| `A_MEN` | 1 | `1'b1` | Memory enabled every cycle |
| `A_WEN` | 1 | `wen` | Write `A_DIN` to `A_ADDR` |
| `A_REN` | 1 | `~wen` | Read when not writing. With `A_WEN` and `A_REN` both high the macro writes and returns the new word (write-through) [5], [7]. Tying `A_REN` to `~wen` rules that out |
| `A_ADDR` | 9 | `addr` | |
| `A_DIN` | 16 | `din` | |
| `A_DOUT` | 16 | `dout` | |
| `A_BM` | 16 | All ones | Bit mask: every write covers the whole word |
| `A_DLY` | 1 | `1'b1` | Must be 1. IHP's model stops the simulation otherwise [7] |
| `A_BIST_*` | | All 0 (`A_BIST_EN` = 0 selects the normal port) | The BIST port is unused |

`A_DLY` high, `A_BM` all ones and the BIST port tied off match the silicon-tested sg13g2 design [5], [6].

### Behaviour

At each rising edge of `clk`:

| `wen` | Macro | `dout` after the edge |
|-------|-------|-----------------------|
| 1 | Writes `din` to `addr` | Keeps its value |
| 0 | Reads `addr` | The word at `addr` |

The behavioural model behaves the same way, so RTL and gate-level simulation agree. IHP's model is the reference: it updates `A_DOUT` only on a read or a write-through [7].

**Latency.** `dout` holds the word from the address presented at the previous rising edge, so a read takes one cycle in the SRAM. The SRAM controller's documented timing already allows for this cycle: two cycles per request ([sram_control](sram_control.md)).

**What `sram_control` must guarantee:**

- `addr`, `wen` and `din` are stable at the rising edge;
- read data is taken from `dout` one cycle after the address;
- `dout` is not expected to change in a write cycle.

The SRAM has one port, so the controller still arbitrates between the I/O Unit's writes and the RTU's reads.

**Timing margins** at the slow corner (1.08 V, 125 °C), from the macro's Liberty file, against the 40 ns clock:

| Parameter | Value |
|-----------|-------|
| `A_CLK` to `A_DOUT` | 6.3 to 6.5 ns |
| Setup before `A_CLK` | At most 1.0 ns (`A_MEN`, `A_WEN`) |
| Hold after `A_CLK` | At most 1.4 ns (`A_ADDR`); the flow inserts hold buffers where needed |
| Minimum `A_CLK` pulse width | 0.5 ns |

**Power.** With `A_MEN` tied high the macro is enabled every cycle, as in the silicon-tested design [6]. Driving `A_MEN` only on real accesses would save power, but changes how the macro is exercised [5].

## Using a different macro size

### Which macros fit

The single-port IHP macros [1], [7]:

- share the same power pins and the same pin edge;
- all except `RM_IHPSG13_1P_64x16_c2` and `RM_IHPSG13_1P_8192x32_c4` have the same port list, with widths that follow the size. Those two have no `A_BM` and no BIST port.

**Upright only.** On the CMOS5L tile a macro can only be placed upright (orientation N or FS).

- Rotated by 90°, its Metal4 supply columns would run horizontally. Every vertical Metal4 stripe would then cross both `VPWR` and `VGND` columns.
- So a macro must be shorter than the core: 306.18 µm in a project two tiles high (`…x2`), 703.08 µm in one four tiles high (`…x4`).
- The tile sizes on Tiny Tapeout's memory page [1] assume the macro can be rotated, as on the earlier sg13g2 tiles, so they do not apply to CMOS5L.

| Macro | Words × bits | Size (µm) | Share of a 4x2 tile | Fits in 4x2 upright |
|-------|--------------|-----------|---------------------|---------------------|
| `RM_IHPSG13_1P_64x16_c2` | 64 × 16 | 236.80 × 64.36 | 5.7% | Yes |
| `RM_IHPSG13_1P_256x16_c2_bm_bist` | 256 × 16 | 236.80 × 118.78 | 10.5% | Yes |
| `RM_IHPSG13_1P_512x16_c2_bm_bist` (current) | 512 × 16 | 236.80 × 191.34 | 16.9% | Yes |
| `RM_IHPSG13_1P_1024x16_c2_bm_bist` | 1024 × 16 | 236.80 × 336.46 | 29.7% | No: needs a project four tiles high (3x4 or larger) |
| `RM_IHPSG13_1P_4096x16_c3_bm_bist` | 4096 × 16 | 416.64 × 618.30 | 96.1% | No: needs a project four tiles high |
| `RM_IHPSG13_1P_512x32_c2_bm_bist` | 512 × 32 | 416.64 × 191.34 | 29.7% | Yes |
| `RM_IHPSG13_1P_512x64_c2_bm_bist` | 512 × 64 | 784.48 × 191.34 | 56.0% | Yes |
| Two `RM_IHPSG13_1P_512x16_c2_bm_bist` side by side | 1024 × 16 | 473.60 × 191.34 | 33.8% | Yes (untested) |

Every word of the scene is 16 bits ([Scene Encoding](../../encoding/scene.md)), so the 16-bit macros are the ones that matter. More words per word size means more scene memory; a different word width would change the scene encoding itself.

### What to change

1. **Choose the macro and the tile.**
    - Check the macro's height against the core height above.
    - A taller macro needs a larger tile: change `tiles` in `info.yaml` (Tiny Tapeout charges by tile).
    - Check the macro's LEF for pins outside the bottom edge. All the current single-port macros have them on the bottom edge only.
2. **Widths.** Change `ADDR_WIDTH` (and `DATA_WIDTH`, if the word width changes) in `src/tinytracer_pkg.sv`.
    - `tt_um_tinytracer`, `sram_control`, `sram_rd_if` and `sram_wr_if` take their widths from these parameters.
    - So do the behavioural model and the macro's `A_BM` tie-off in `scene_sram`.
3. **`src/scene_sram.sv`.** Change the module name of `u_sram`.
    - For `RM_IHPSG13_1P_64x16_c2` or `RM_IHPSG13_1P_8192x32_c4`, remove the `A_BM` and `A_BIST_*` connections: those macros do not have them.
    - Keep `A_REN = ~wen`, `A_DLY = 1` and `(* keep *)`.
4. **Everything that assumes 512 words.** Update:
    - the address counters and scene layout in the RTU and I/O Unit;
    - the scene encoding ([Scene Encoding](../../encoding/scene.md): "up to 511");
    - the UART object frame. `OBJ_ADDR` already carries 16 bits, but the [UART Frame Encoding](../../encoding/uart_frame.md) defines only 9 of them;
    - the 512-word statements in the [introduction](../../introduction.md), [tinytracer_if](../tinytracer_if.md), [sram_control](sram_control.md), [scene_sram](scene_sram.md) and [tt_um_tinytracer](../tt_um_tinytracer.md).
5. **`src/config.json`.**
    - Rename the `MACROS` key, and the six view paths under it (GDS, LEF, CDL and three Liberty files), to the new macro.
    - Keep the placement at (3.36, 3.78) µm with orientation FS unless the macro no longer fits there.
    - `PDN_MACRO_CONNECTIONS` and `MAGIC_EXT_ABSTRACT_CELLS` work unchanged for every single-port macro: same pin names, and the pattern matches every IHP SRAM name.
6. **Power.** `odb_stripes.py` finds any IHP SRAM by its `VDD!` and `VSS!` pins and works out the columns from its LEF, so a single macro needs no change.
    - Check the `project-extendpowerstripes` log: every region should get at least two pairs.
    - Then run `check_power_grid`.
7. **`test/Makefile`.** Change the macro model's file name in the gate-level section.
8. **Docs.** Update [scene_sram](scene_sram.md), [tt_um_tinytracer](../tt_um_tinytracer.md) and this page.
9. **Verify.** Run the local flow and CI ([Verifying a change](#verifying-a-change)): LVS, KLayout DRC, the precheck, the power-grid check and the gate-level test.

### Two macros for 1024 words

Two `RM_IHPSG13_1P_512x16_c2_bm_bist` macros side by side fit a 4x2 tile and double the scene memory. This has not been built. It would need:

- **RTL:** two instances in `scene_sram`, one selected by `addr[9]` (`ADDR_WIDTH = 10`).
    - Each instance's `wen` and `A_REN` are gated by its select bit.
    - `dout` comes from the instance selected by `addr[9]` at the previous edge. The read data arrives a cycle after the address, so the select bit must be registered.
- **`src/config.json`:**
    - two instances under the `MACROS` key, e.g. at x = 3.36 µm and at x = 3.36 + 236.80 µm plus at least the macro halo (`FP_MACRO_HORIZONTAL_HALO`);
    - both `PDN_MACRO_CONNECTIONS` lines repeated for each instance.
- **Power:** `odb_stripes.py` handles each SRAM it finds [2]. Check its log for both macros.

### Dual-port macros

IHP also has dual-port macros (`RM_IHPSG13_2P_*`) [1], [7]. They would let the I/O Unit and the RTU access the scene at the same time without the controller's arbitration. They are larger: the 512×16 version is 402.61 × 219.77 µm according to [1]. Their two ports are named `A_*` and `B_*`. Before using one, check that its power pins and Metal4 columns follow the single-port layout, because `odb_stripes.py` and the settings above assume it.

## Sources


1. Tiny Tapeout, "Memory" (macro list, sizes and the note that integration is not trivial): <https://tinytapeout.com/specs/memory/>

2. Ken Pettit (kdp1965), "SRAM macro integration in IHP CMOS5L", and the ihp-um-janestreet-prism repository. Used for:
    - the power-grid approach, the `Project.ExtendPowerStripes` step, and `odb_stripes.py`, copied from commit `28350386cee5d29801ef29337b8f2da3f187fc55`;
    - the macro's placement and orientation;
    - the sign-off settings.

    Links: <https://kdp1965.github.io/ihp-um-janestreet-prism/ihp_sram_macro.html>, <https://github.com/kdp1965/ihp-um-janestreet-prism>

3. William Zhang, protocol-emulator. Used for:
    - `src/pdn_cfg.tcl`, from commit `b837d90c5d0e632b0c17f865fc789b7431d44abf`;
    - the netgen LVS JSON fix;
    - `ERROR_ON_PDN_VIOLATIONS` and the other settings that pass the standard Tiny Tapeout CI with an IHP SRAM.

    Link: <https://github.com/WilliamZhang20/protocol-emulator>

4. TeslaCoilerOW, ttihp-protocol-emulator (why the Magic illegal overlaps at the `VDD!`/`VDDARRAY!` break are false): <https://github.com/TeslaCoilerOW/ttihp-protocol-emulator>

5. Matt Venn, multi-seg-monitor (sg13g2, TTIHP26b). Used for:
    - the pin tie-offs and the write-through behaviour;
    - the Liberty `max_capacitance` units bug;
    - `MAGIC_MACRO_STD_CELL_SOURCE` and `MAGIC_EXT_ABSTRACT_CELLS`;
    - its `SRAM.csv` list of Tiny Tapeout SRAM projects.

    Link: <https://github.com/mattvenn/multi-seg-monitor>

6. Uri Shaked, ttihp-sram-test (`RM_IHPSG13_1P_1024x8_c2_bm_bist` on TTIHP0p2, tested in silicon): <https://github.com/urish/ttihp-sram-test>, <https://tinytapeout.com/chips/ttihp0p2/tt_um_urish_sram_test>

7. IHP-Open-PDK, commit `2bbec755dc67ca3db0261c3d6163e15735d66710`. Used for the macro's GDS, LEF, CDL, Liberty timing and behavioural model (`RM_IHPSG13_1P_core_behavioral_bm_bist.v`: the write-through and `A_DLY` behaviour): <https://github.com/IHP-GmbH/IHP-Open-PDK>

8. TinyTapeout/tt-gds-action, branch `ihp-cmos5l`. Used for:
    - the pinned PDK (`install_sg13cmos5l.sh`) and the LibreLane version;
    - the steps of the gate-level test job.

    Link: <https://github.com/TinyTapeout/tt-gds-action/tree/ihp-cmos5l>

9. TinyTapeout/tt-support-tools, branch `ihp-sg13cmos5l`. Used for:
    - tile sizes and the Metal4 top layer;
    - the precheck's layer list and power-port width.

    Links: <https://github.com/TinyTapeout/tt-support-tools/tree/ihp-sg13cmos5l>, PR #187 "Allow SRAM and DigiBnd layers in SG13CMOS5L precheck" <https://github.com/TinyTapeout/tt-support-tools/pull/187>, and issue #190 (sg13g2 DRC inside an SRAM macro; the CMOS5L deck reports none) <https://github.com/TinyTapeout/tt-support-tools/issues/190>

10. TinyTapeout/ttihp-verilog-template, branch `cmos5l` (the CMOS5L project template): <https://github.com/TinyTapeout/ttihp-verilog-template/tree/cmos5l>

11. LibreLane configuration reference (the variables used above): <https://librelane.readthedocs.io/en/latest/reference/configuration.html>

12. cocotb 1.9.2 (`share/makefiles/Makefile.inc` exports `PYTHONHOME` outside a venv): <https://pypi.org/project/cocotb/1.9.2/>

13. UW-ASIC/TinyTracer GitHub Actions, the `sram-macro` run in which the GDS, precheck and gate-level jobs all passed: <https://github.com/UW-ASIC/TinyTracer/actions/runs/36952296434>
