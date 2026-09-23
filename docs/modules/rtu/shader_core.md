---
description: "Colours a ray from its intersection result, the hit object's material, and the sky colour."
---

# `shader_core` — Colours pixels based on ray-object intersection results and material metadata

## Overview

This module uses the results of a ray-object intersection, the intersected object's metadata (i.e. material, colour), and the sky colour to compute the colour for a ray.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `MAX_BOUNCES`  |     10     | Ray bounce limit             |
| `WLEN`  |     16      | Word length              |
| `MACRO_W`  |     101     | Macro operation width             |
| `COLOUR_DEPTH`  |     8    | Bits per colour channel            |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |
| `sky_colour`  |     struct      | Sky colour |
| `object_colour`  |     struct      | Intersected object's colour |
| `mat_type`  |     2      | Intersected object's material type |
| `ray_bounces_left`  |     `clog2(MAX_BOUNCES)`      | Ray bounces remaining |
| `hit`  |     1      | Ray-object intersection flag |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| `colour_if`  | Sample pixel colour stream to the Accumulator |
| `macro_if`  | Macro-op request and response channel to the Decode Unit |

## Architecture Overview