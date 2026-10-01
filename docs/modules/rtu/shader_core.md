---
description: "Tracks the light a ray path carries and colours each sample from the hit object's material, the sky, or the ground."
---

# `shader_core` — Colours pixels based on ray-object intersection results and material metadata

## Overview

This module uses the results of a ray-object intersection, the intersected object's metadata (i.e. material, colour), and the sky and ground colours to compute the colour of a sample. It keeps the attenuation, the light the ray path still carries, and updates it at each surface the path hits.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `WLEN`  |     16      | Word length              |
| `MACRO_W`  |     102     | Macro operation width             |
| `COLOUR_DEPTH`  |     8    | Bits per colour channel            |
| `SAMPLE_DEPTH`  |     12    | Bits per sample colour channel            |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |
| `start`  |     1      | Start signal from the Controller |
| `mode`  |     2      | 0: sky sample, 1: glow sample, 2: surface (attenuation update), 3: bounce limit |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `done`  |     1      | One-cycle pulse: the attenuation is updated (mode 2), or the Accumulator has taken the sample (modes 0, 1, 3) |

### Registers

The Shader Core works on the RTU's shared registers (see [RTU](rtu.md#ray-state-registers)) and sends its macro-ops through the RTU request path (see [Handshakes](rtu.md#handshakes)). The signals it uses to select operand sources and to write registers are not defined yet.

| Access | Registers |
|----|----|
| Reads | Sky and ground colours (header registers); $D_z$; hit kind; hit point x and y (checker); the closest object's colour and glow strength |
| Writes | Attenuation (3 $\times$ 8), sample (3 $\times$ 12) |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| [`colour_if.src`](../tinytracer_if.md#colour_if)  | Sample colour stream to the Accumulator (`W` = `SAMPLE_DEPTH`) |
| [`rtu_req_if.client`](../tinytracer_if.md#rtu_req_if)  | Macro-op requests and responses through the RTU request path |

## Architecture Overview

All colour arithmetic is on integers, per colour channel. $c$ is the surface colour: the object's colour, or on the ground the checker colour A or B (colour B where bit 9 of the hit point's raw x XOR bit 9 of its raw y is 1).

| Event | Computes | Cycles |
|----|----|:----:|
| Start of a sample | attenuation = 255 (set by the Controller) | 0 |
| Surface hit (ground, matte, mirror, glass) | attenuation = attenuation $\times (c + 1) \gg 8$, one `M_VMUL` | 7 |
| Sky | $L$ = horizon + (top - horizon) $\times D_z$, with $D_z < 0$ read as 0; sample = (attenuation + 1) $\times L \gg 8$ | 28 |
| Glow object | sample = ((attenuation + 1) $\times c \gg 8$) $\times$ strength $\gg 10$ | — |
| Bounce limit reached | sample = 0 | 0 |

- The + 1 keeps white at full strength: 255 $\times$ 256 $\gg$ 8 = 255. The multiplier rounds
- The sky fades from the horizon colour ($D_z$ = 0) to the top colour ($D_z$ = 1)
- The glow strength is Q4.10 (0 to 15.99), so a glow sample can be up to 4080 per channel: 12 bits. The Accumulator clamps the average to 255
- The sample goes to the Accumulator over `colour_if`, and `done` follows in the cycle the Accumulator takes it

The shifts of 8 and 10 cannot be selected with the 1-bit `FMT` field of a macro-op. This is still open: either `FMT` becomes a 2-bit select, or the Shader Core gets its own colour multiplier (see [Instruction Encoding](../../encoding/instruction.md)).
