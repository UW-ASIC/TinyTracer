---
description: "Buffer that averages per-pixel sample colours from the RTU before sending them to the I/O Unit."
---

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
| [`colour_if.sink`](../tinytracer_if.md#colour_if)  | Sample colour stream from the RTU |
| [`colour_if.src`](../tinytracer_if.md#colour_if)  | Pixel colour stream to the I/O Unit |

## Architecture Overview

The accumulator module holds the per-component sum of the sampled pixel colours (`colour_if.sink.colour.r`, `colour_if.sink.colour.g`, `colour_if.sink.colour.b`), where the number of samples is determined by the `SPP` parameter. It is important to note that `SPP` must be a power of two to facilitate efficient averaging through bit-shifting or bit-slicing operations. The internal width of the accumulator is calculated as `COLOUR_DEPTH + log2(SPP)` to ensure that the sum does not overflow during accumulation.

After accumulating `SPP` samples, the module computes the average colour by performing a right bit-shift operation on the accumulated sum. The averaged colour is then sent to the I/O Unit through `colour_if.src`, with `colour_if.src.valid` asserted to indicate that valid data is available. The `colour_if.src.ready` signal reflects whether the downstream consumer is ready to accept the averaged colour. If the consumer is not ready, this backpressure is propagated upstream by deasserting `colour_if.sink.ready`, preventing the accumulator from accepting additional samples until the downstream interface is ready to proceed.

Input samples are accumulated only when both `colour_if.sink.valid` and `colour_if.sink.ready` are asserted. When `colour_if.src.ready` is deasserted by the downstream consumer, `colour_if.sink.ready` is also deasserted so that no further input samples are accepted. The module also handles the reset condition appropriately by clearing the accumulated values and sample count, and deasserting `colour_if.src.valid` when `rst_n` is asserted low.

