# `ray_generator` — Generates primary and secondary rays

## Overview

This module generates primary and secondary rays to check for ray-object intersection. Primary rays originate from the camera origin, while secondary rays originate from the surface of an object that has been hit by a previous ray.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `WLEN`  |     16      | Word length              |
| `MACRO_W`  |     101     | Macro operation width             |
| `IMG_W`  |     64      | Output image width |
| `IMG_H`  |     64      | Output image height |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |
| `mode`  |     1      | Selects primary (`mode` = 0) or secondary (`mode` = 1) ray generation |
| `collision_point`  |     struct      | Point of ray-object intersection |
| `ray_dir`  |     struct      | Direction of incident ray |
| `mat_type`  |     2      | Intersected object's material type |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `gen_ray_origin`  |     struct      | Origin of generated ray |
| `gen_ray_dir`  |     struct      | Direction of generated ray |
| `gen_ray_valid`  |     1      | Generated ray valid |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| `macro_if`  | Macro-op request and response channel to the Decode Unit |

## Architecture Overview