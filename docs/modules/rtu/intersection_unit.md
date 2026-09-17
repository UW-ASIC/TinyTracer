# `intersection_unit` — Computes ray-object intersection

## Overview

This module checks if an incident ray intersects any objects in the scene and provides the point of ray-object intersection if a hit occurs. Intersection calculations are determined by the primitive type, with ray-sphere intersection using the quadratic formula and ray-triangle intersection using the Möller-Trumbore method.

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
| `prim_type`  |     1      | Primitive type of intersected object (sphere or triangle)   |
| `ray_origin`        |     `3*WLEN`     | Incident ray origin           |
| `ray_dir`        |     `3*WLEN`     | Incident ray direction            |
| `origin`        |      `3*WLEN`     | Origin of intersected object            |
| `u`        |     `3*WLEN`     | Triangle plane vector           |
| `v`        |     `3*WLEN`     | Triangle plane vector          |
| `radius`        |      `WLEN`     | Sphere radius            |
| `macro_req_ready`        |     1     | Decode Unit can accept macro-ops          |
| `macro_resp_valid`        |     1    | Macro-op result is valid         |
| `macro_resp_result`        |      `3*WLEN`     | Macro-op result           |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `collision_point`  |     `3*WLEN`      | Point of ray-object intersection              |
| `hit`  |     1     | Object hit flag              |
| `macro_req_valid`  |     1      | Macro-op valid            |
| `macro_req_op`        |     `MACRO_W`     | Macro-op           |
| `macro_resp_ready`        |     1     | RTU can accept macro-op result           |

## Architecture Overview