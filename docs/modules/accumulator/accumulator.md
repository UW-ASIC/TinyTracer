# `accumulator` — Buffer between the RTU and I/O Unit

## Overview

This module stores sampled pixel colours from the RTU and computes their average once `SPP` samples have been computed for a given pixel. The averaged result is subsequently sent to the I/O Unit.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `COLOUR_DEPTH`  |     8      | Bits per RGB color channel               |

## Interface

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal               |
| `rst_n`  |     1     | Active-low reset              |
| `sample_req_valid`  |     1      | RTU pixel sample is valid            |
| `sample_req_colour`        |     `3*COLOUR_DEPTH-1`     | RTU sample pixel colour           |
| `pixel_req_ready`        |     1     | I/O Unit can accept average pixel colour result         |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `sample_req_ready`  |     1      | RTU pixel sample data can be accepted               |
| `pixel_req_valid`  |     1     |  Accumulator average pixel colour data is valid       |
| `pixel_req_colour`  |     `3*COLOUR_DEPTH-1`      | Average pixel colour data          |

## Architecture Overview