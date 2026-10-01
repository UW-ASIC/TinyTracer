---
description: "Ray Tracing Unit that sequences the ray-tracing algorithm with an FSM and issues instructions to the Execution Unit."
---

# `rtu` — Instantiates Ray Generator, Intersection Unit, and Shader Core

## Overview

This module uses a finite-state machine (FSM) to execute each step of the ray-tracing algorithm. Each step of the algorithm is a series of computations, where each computation is encoded as an instruction. These instructions are sent to the Execution Unit, whose Decode Unit decomposes more complex instructions (like vector operations) into simple "micro-operations" that the individual scalar FUs can process. The RTU does no arithmetic itself. The RTU controls the Ray Generator, Intersection Unit, and Shader Core submodules to compute the sample colours of each pixel, and holds the registers and request path they share.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `ADDR_WIDTH`  |     9      | SRAM address width             |
| `DATA_WIDTH`  |     16     | SRAM data width             |
| `WLEN`  |     16      | Word length              |
| `MACRO_W`  |     102     | Macro operation width             |
| `COLOUR_DEPTH`  |     8    | Bits per colour channel            |
| `SAMPLE_DEPTH`  |     12    | Bits per sample colour channel            |
| `MAX_BOUNCES`  |     8      | Ray bounce limit |
| `DIM_WIDTH`  |     12      | Width of the image width and height from the I/O Unit |
| `SPP_LOG2_W`  |     3      | Width of $\log_2$ of the samples per pixel |
| `HDR_WORDS`  |     17      | Number of header words, at SRAM address 0 |
| `MAX_BV`  |     16      | Largest number of bounding volumes |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `spp_log2`  |     `SPP_LOG2_W`      | $\log_2$ of the samples per pixel, from the header, to the Accumulator |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| [`render_if.sink`](../tinytracer_if.md#render_if)  | Render strobe and image dimensions from the I/O Unit |
| [`sram_rd_if.client`](../tinytracer_if.md#sram_rd_if)  | SRAM read request and response channel |
| [`macro_if.client`](../tinytracer_if.md#macro_if)  | Macro-op request and response channel to the Execution Unit |
| [`colour_if.src`](../tinytracer_if.md#colour_if)  | Sample colour stream to the Accumulator (`W` = `SAMPLE_DEPTH`) |

## Architecture Overview

The RTU is made of the Controller (the RTU's own FSM), the [Ray Generator](ray_gen/ray_generator.md), the [Intersection Unit](intersection_unit.md), and the [Shader Core](shader_core.md), together with the header registers, the ray state registers, and the request path that they share. The Controller starts one sub-block at a time; the active sub-block sends its macro-ops through the request path and reads the SRAM. In `rtu.sv`, the sub-blocks connect to the request path through the `rtu_req_if` instances `rg_req`, `iu_req`, and `sh_req`, the Intersection Unit's SRAM port through the `sram_rd_if` instance `iu_sram`, and the Shader Core's `sample` port straight to the RTU's.

### Controller

When `render.render` is pulsed, the Controller reads the 17 header words (see [Scene Encoding](../../encoding/scene.md#header)) into the header registers, 2 cycles per word (34 cycles). It never reads them again during the render. It then runs three nested loops:

1. __Pixels__: row by row, with 9-bit pixel x and y counters
2. __Samples__: $s$ samples per pixel, where $\log_2 s$ is the header's `SPP_LOG2` (1 to 32 samples), with a 5-bit sample counter. Each sample is one ray path through a slightly different point of the pixel
3. __Segments__: one straight piece of the path, from its origin to the first thing it hits. A path has up to 9 segments: the camera ray and up to 8 bounces, counted by a 4-bit bounce counter that exists only in the Controller

One sample runs as follows. At its start, the Controller sets the attenuation to 255 and the bounce count to 0. It then starts one sub-block at a time, with the `mode` shown, and picks the next step from what the sub-block reports (see [Handshakes](#handshakes)):

| Step | Sub-block (`mode`) | Next step |
|:----:|----|----|
| 1 | Ray Generator (0: camera ray) | 2 |
| 2 | Intersection Unit (0: search for the closest hit) | By `hit_kind`: sky 3, ground 5, object 4 |
| 3 | Shader Core (0: sky sample) | Sample done |
| 4 | Intersection Unit (1: read the closest object's colour, strength, and material) | By `material`: glow 6, otherwise 5 |
| 5 | If the bounce count is 8: Shader Core (3: bounce limit, black sample). Otherwise: Intersection Unit (2: hit point and surface normal) | Bounce limit: sample done. Otherwise 7 |
| 6 | Shader Core (1: glow sample) | Sample done |
| 7 | Shader Core (2: attenuation) | 8 |
| 8 | Ray Generator (1: new direction, move the origin off the surface); the bounce count increments | 2 |

The sky covers nothing hit, a ray that points up, and a ground that is too far away. When a sample is done, the Shader Core has handed it to the Accumulator, and the Controller starts the next sample at step 1, or, after $s$ samples, the next pixel.

### Header Registers

| Register | Bits | Header words |
|----|:----:|:----:|
| `F`, `R`, `U` | 9 $\times$ 16 (DIR) | `w0`-`w8` |
| sky colours: horizon, top | 2 $\times$ 24 | `w9`-`w11` |
| ground colours: A, B | 2 $\times$ 24 | `w12`-`w14` |
| `BV_NUM`, `SPP_LOG2` | 5, 3 | `w15` |
| `CAM_Z` | 16 (POS) | `w16` |

### Ray State Registers

| Register | Bits | Written by | Read by |
|----|:----:|----|----|
| $O$: ray origin, then hit point | 3 $\times$ 16 (POS) | Ray Generator (camera ray, push off), Intersection Unit (hit point) | Intersection Unit, Ray Generator, Shader Core |
| $D$: ray direction | 3 $\times$ 16 (DIR) | Ray Generator | Intersection Unit, Ray Generator, Shader Core |
| $n$: surface normal | 3 $\times$ 16 (DIR) | Intersection Unit | Ray Generator |
| best $t$, best address, hit kind (sky, ground, object) | 16, 9, 2 | Intersection Unit | Intersection Unit, Shader Core, Controller |
| kept test values: sphere $\text{offset}_s$, $\text{half}_s$, $r_s$; flip bit; triangle $K$ | 5 $\times$ 16, 1, 5 | Intersection Unit (new best hit) | Intersection Unit (normal), Ray Generator (glass) |
| material | 2 | Intersection Unit (mode 1; matte for the ground in mode 0) | Ray Generator, Controller |
| closest object's colour, glow strength | 3 $\times$ 8, 14 | Intersection Unit (mode 1) | Shader Core |
| scratch | 7 $\times$ 16 | Intersection Unit (test values), Ray Generator (matte bounce) | same |
| BV address, BVs left, object address, objects left | 9, 5, 9, 7 | Intersection Unit | Intersection Unit (SRAM address) |
| attenuation, sample | 3 $\times$ 8, 3 $\times$ 12 | Controller (attenuation = 255 at the start of a sample), Shader Core | Shader Core, Accumulator (sample, over `colour_if`) |
| pixel x, y; sample count; bounce count | 9 + 9, 5, 4 | Controller | Controller; Ray Generator (pixel x, y) |

The best hit keeps the values its test left behind, so the closest object's test never runs a second time (see [Intersection Unit](intersection_unit.md)).

### Request Path

The active sub-block builds each macro-op in a shared request register, which drives `macro.req_op` (see [Handshakes](#request-path-handshake) for the signals):

- __Request register__: 102 bits, split into 8 fields (`FMT`, $u_3$, $u_2$, $u_1$, $v_3$, $v_2$, $v_1$, `MACROOP`; see [Instruction Encoding](../../encoding/instruction.md)). Each field has its own write enable, so a field that the next macro-op does not change is not written. For example, the triangle test computes $\det = e_1 \cdot P$ and then $\alpha_{top} = \text{slid} \cdot P$, and only $\mathbf{\vec{u}}$ changes between the two
- __Operand select__: each of the six 16-bit operand fields is loaded from one of six sources: the ray state registers, the header registers, the SRAM word being read, the last macro-op result, LFSR bits from the [RNG](ray_gen/rng.md), or a constant
- __Size shifter__: shifts a field by the size shift $K$, or applies the resize pre-shift before `M_NORM`. A leading-one finder picks the shift. Both are wiring, 0 cycles (see [Number Formats](../../encoding/number_format.md#shifts-in-the-rtu-request-path))
- __Sign flip__: XORs a field with a control bit, which negates it without an adder (for example, random signs in the matte bounce)

A macro-op result goes into the next request, into the ray state registers, or back to the active sub-block as a 1-bit compare flag. The sub-blocks check each flag as it arrives and stop a test at the first failed check.

The active sub-block (the Controller at render start, and the Intersection Unit in any of its modes) drives the SRAM read address. Each word takes 2 cycles; SRAM reads do not overlap macro-ops.

### Handshakes

The handshakes inside the RTU let one macro-op follow another with no idle cycle, including when the Controller hands over from one sub-block to the next. The cycle counts in the sub-block pages assume this.

#### Controller and Sub-Blocks

Each sub-block has `start`, `mode`, and `done` signals to the Controller:

- The Controller starts a sub-block with a one-cycle pulse on `start`, with `mode` valid in the same cycle. The sub-block registers `mode` at the end of that cycle and works from the next cycle. It ignores `start` while it is busy
- The sub-block pulses `done` for one cycle in the cycle it finishes: the cycle of its last macro-op response, SRAM word, or sample transfer. Register writes it makes in that cycle take effect at the end of the cycle
- Anything the Controller needs to pick the next step is an output of the sub-block, valid in the cycle of `done`: the Intersection Unit's `hit_kind` (mode 0) and `material` (mode 1)
- The Controller can pulse the next sub-block's `start` in the same cycle as `done`, so the next sub-block can send its first macro-op in the following cycle

#### Active Block

The Controller keeps an `active` register (`rtu_blk_t`: `BLK_CTRL` = 0, `BLK_RAY_GEN` = 1, `BLK_ISECT` = 2, `BLK_SHADER` = 3). It sets `active` to the sub-block it starts, at the end of the cycle of the `start` pulse, and to itself while it reads the header. Only the active block's request path signals and SRAM read requests reach the request register, `macro`, and `sram`; the other blocks' are ignored.

#### Request Path Handshake

Each sub-block connects to the request path through [`rtu_req_if`](../tinytracer_if.md#rtu_req_if):

- __Field writes__: in any cycle, the active block can write fields of the request register. `req_we` has one write enable per field, in the order `FMT`, $u_3$, $u_2$, $u_1$, $v_3$, $v_2$, $v_1$, `MACROOP`. `req_fmt` and `req_op` carry the values for `FMT` and `MACROOP`. The operand fields take their values from the operand select, size shifter, and sign flip, whose controls are not defined yet. Writes take effect at the end of the cycle
- __Bypass__: `macro.req_op` is the request register with the current cycle's writes applied, so a block can write the last fields of a macro-op and send it in the same cycle
- __Send__: the block raises `req_valid` to send the request register as a macro-op; `req_ready` is `macro.req_ready`. The macro-op is sent in the cycle both are high. While `req_valid` is high and `req_ready` is low, the block keeps its field writes the same. A block sends a macro-op only after the response to its previous one
- __Response__: the RTU takes every response at once (`macro.resp_ready` is always 1) and passes it to the active block: `resp_valid` is high for one cycle, `resp_flag` is bit 0 of `resp_result.x` (the compare flag), and `resp_result` is the whole result. In that cycle the block can write fields of its next request from the result, and write the result into ray state registers
- __Timing__: a macro-op whose response arrives in cycle $t$ can be followed by the next macro-op in cycle $t + 1$, the first cycle the Decode Unit can accept it (see [Decode Unit](../exu/decode.md#timing-behaviour))

#### SRAM Reads

- The active block reads the SRAM through the RTU's `sram_rd_if`: the Controller directly, and the Intersection Unit through its own `sram_rd_if.client` port, which the RTU connects to `sram` while it is active. The RTU keeps `sram.resp_ready` high
- The SRAM Controller takes the next address in the cycle a word comes back, so reads take 2 cycles per word
- A block does not read the SRAM while it has a macro-op in flight
- A word can be written into a request field or a header register in the cycle it arrives (`sram.resp_valid`)

#### Samples

The Shader Core sends each sample to the Accumulator over `colour_if` and pulses `done` in the cycle the Accumulator takes it. The Accumulator's `ready` is low while it holds a finished pixel that the I/O Unit has not taken yet, so the first sample of the next pixel waits there when the UART falls behind. `spp_log2` comes from the header registers and does not change during a render.

#### Random Numbers

The [RNG](ray_gen/rng.md)'s `rand_num` is valid in every cycle. The Ray Generator passes it to the request path as the LFSR operand source, and pulses the RNG's `req` in each cycle a field is written from it, so each random number is used once.

### Cycles

The cycle counts in the sub-block pages assume that the Controller and sub-blocks add no cycles between macro-ops, which the [handshakes](#handshakes) allow. On the demo scene (`sim/scene_demo.txt`), a segment takes 658 cycles on average and a sample 1.81 segments, so a 512 $\times$ 512 frame at 25 MHz takes about 6.7 minutes at 32 samples per pixel and 1.7 minutes at 8 (see [Introduction](../../introduction.md#performance)).
