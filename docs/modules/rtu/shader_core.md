# `shader_core` — Colours pixels based on ray-object intersection results and material metadata

## Overview

This module uses the results of a ray-object intersection, the intersected object's metadata (i.e. material, colour), and the sky colour to compute the colour for a ray.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `MAX_BOUNCES`  |     8     | Ray bounce limit             |
| `WLEN`  |     16      | Word length              |
| `MACRO_W`  |     101     | Macro operation width             |
| `COLOUR_DEPTH`  |     8    | Bits per colour channel            |

## Interface

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal               |
| `rst_n`  |     1     | Active-low reset              |
| `sky_colour` | `3*WLEN` | Sky colour |
| `object_colour`        |     `3*WLEN`     | Intersected object's colour          |
| `mat_type`        |      2     | Intersected object's material type           |
| `ray_bounces_left`        |     `log2(MAX_BOUNCES)`     | Ray bounces remaining           |
| `hit`        |     1     | Ray-object intersection flag         |
| `mat_type`        |      2     | Intersected object's material type           |
| `ray_bounces_left`        |     `log2(MAX_BOUNCES)`     | Ray bounces remaining           |
| `sample_req_ready`        |      1     | Accumulator can accept pixel sample data           |
| `macro_req_ready`        |     1     | Decode Unit can accept macro-ops          |
| `macro_resp_valid`        |     1    | Macro-op result is valid         |
| `macro_resp_result`        |      `3*WLEN`     | Macro-op result           |


### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `sample_req_valid`        |     1     | RTU pixel sample data valid           |
| `sample_req_colour`        |     `3*COLOUR_DEPTH`     | RTU pixel sample data           |
| `macro_req_valid`  |     1      | Macro-op valid            |
| `macro_req_op`        |     `MACRO_W`     | Macro-op           |
| `macro_resp_ready`        |     1     | RTU can accept macro-op result           |

## Architecture Overview