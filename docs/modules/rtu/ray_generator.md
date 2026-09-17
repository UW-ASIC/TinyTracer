# `ray_generator` — Generates primary and secondary rays

## Overview

This module generates primary and secondary rays to check for ray-object intersection. Primary rays originate from the camera origin, while secondary rays originate from the surface of an object that has been hit by a previous ray.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `WLEN`  |     16      | Word length              |
| `MACRO_W`  |     101     | Macro operation width             |

## Interface

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal               |
| `rst_n`  |     1     | Active-low reset              |
| `mode`  |     1      | Selects primary (`mode` = 0) or secondary (`mode` = 1) ray generation |
| `collision_point`        |     `3*WLEN`     | Point of ray-object intersection           |
| `surface_norm`        |     `3*WLEN`     | Incident ray direction           |
| `ray_dir`        |      `3*WLEN`     | Origin of intersected object            |
| `mat_type`        |     2    | Intersected object's material type           |
| `macro_req_ready`        |     1     | Decode Unit can accept macro-ops          |
| `macro_resp_valid`        |     1    | Macro-op result is valid         |
| `macro_resp_result`        |      `3*WLEN`     | Macro-op result           |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `gen_ray_origin`  |     `3*WLEN`      | Origin of generated ray              |
| `gen_ray_dir`  |     `3*WLEN`     | Direction of generated ray             |
| `gen_ray_valid`  |     1      | Generated ray valid            |
| `macro_req_valid`  |     1      | Macro-op valid            |
| `macro_req_op`        |     `MACRO_W`     | Macro-op           |
| `macro_resp_ready`        |     1     | RTU can accept macro-op result           |

## Architecture Overview