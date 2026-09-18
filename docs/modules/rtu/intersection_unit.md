# `intersection_unit` — Computes ray-object intersection

## Overview

This module checks if an incident ray intersects an object in the scene and provides the point of ray-object intersection if a hit occurs. Intersection calculations are determined by the primitive type, with ray-sphere intersection using the quadratic formula and ray-triangle intersection using the Möller-Trumbore method.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `WLEN`  |     16      | Word length              |
| `MACRO_W`  |     101     | Macro operation width             |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |
| `prim_type`  |     1      | Primitive type of intersected object (sphere or triangle) |
| `ray_origin`  |     struct      | Incident ray origin |
| `ray_dir`  |     struct      | Incident ray direction |
| `origin`  |     struct      | Origin of intersected object |
| `u`  |     struct      | Triangle plane vector |
| `v`  |     struct      | Triangle plane vector |
| `radius`  |     `WLEN`      | Sphere radius |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `collision_point`  |     struct      | Point of ray-object intersection |
| `hit`  |     1      | Object hit flag |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| `macro_if`  | Macro-op request and response channel to the Decode Unit |

## Architecture Overview