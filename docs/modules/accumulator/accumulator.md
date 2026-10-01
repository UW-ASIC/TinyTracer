---
description: "Buffer that averages per-pixel sample colours from the RTU before sending them to the I/O Unit."
---

# `accumulator` — Buffer between the RTU and I/O Unit

## Overview

This module stores sampled pixel colours from the RTU and computes their average once all the samples of a pixel have been computed. The averaged result is subsequently sent to the I/O Unit.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `COLOUR_DEPTH`  |     8      | Bits per RGB colour channel of a pixel               |
| `SPP_LOG2_W`  |     3      | Width of $\log_2$ of the samples per pixel |
| `SAMPLE_DEPTH`  |     12      | Bits per RGB colour channel of a sample               |
| `MAX_SPP`  |     32      | Largest number of samples per pixel |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |
| `spp_log2`  |     `SPP_LOG2_W`      | $\log_2$ of the samples per pixel (0-5), from the RTU's header registers |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| [`colour_if.sink`](../tinytracer_if.md#colour_if)  | Sample colour stream from the RTU (`W` = `SAMPLE_DEPTH`) |
| [`colour_if.src`](../tinytracer_if.md#colour_if)  | Pixel colour stream to the I/O Unit (`W` = `COLOUR_DEPTH`) |

## Architecture Overview

The accumulator module holds the per-component sum of the sampled pixel colours (the r, g, and b fields of `colour_if.sink.colour`), where the number of samples $s$ ($\log_2 s$ = `spp_log2`) comes from the scene header (see [Scene Encoding](../../encoding/scene.md#header)) and is 1, 2, 4, 8, 16, or 32. Because $s$ is a power of two, averaging is a bit shift. The internal width of the accumulator is `SAMPLE_DEPTH + log2(MAX_SPP)` = 17 bits to ensure that the sum does not overflow during accumulation.

After accumulating $s$ samples, the module computes the average colour by shifting the sum right by `spp_log2` and clamping it to 255: a glowing object can make a sample colour larger than 255 (up to 4080). The averaged colour is then sent to the I/O Unit through `colour_if.src`, with `colour_if.src.valid` asserted to indicate that valid data is available, and held until the I/O Unit takes it (`colour_if.src.valid` and `colour_if.src.ready` both high). The accumulator clears its sums in that cycle and starts on the next pixel.

Input samples are accumulated only when both `colour_if.sink.valid` and `colour_if.sink.ready` are asserted. `colour_if.sink.ready` is low only while the accumulator holds a finished pixel that the I/O Unit has not taken yet (`colour_if.src.valid` high and `colour_if.src.ready` low). A low `colour_if.src.ready` on its own, for example while the I/O Unit is still sending the previous pixel over the UART, does not stop samples: the accumulator keeps adding up the next pixel. So the RTU renders one pixel while the I/O Unit sends the one before it, and when the UART falls further behind, the first sample of the pixel after that waits on `colour_if.sink.ready`. The RTU needs no other signal for this.

The module also handles the reset condition appropriately by clearing the accumulated values and sample count, and deasserting `colour_if.src.valid` when `rst_n` is asserted low.
