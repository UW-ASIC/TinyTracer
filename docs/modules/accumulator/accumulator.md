# `accumulator` — Buffer between the RTU and I/O Unit

## Overview

This module stores sampled pixel colours from the RTU and computes their average once `SPP` samples have been computed for a given pixel. The averaged result is subsequently sent to the I/O Unit.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `COLOUR_DEPTH`  |     8      | Bits per RGB colour channel               |
| `SPP`  |     8      | Samples per pixel |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| `colour_if`  | Sample colour stream from the RTU |
| `colour_if`  | Pixel colour stream to the I/O Unit |

## Architecture Overview