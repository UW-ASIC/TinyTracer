---
description: "The UART runs on a separate clock to achieve a desired baud rate, derived from the system clock. To achieve this, we use a fractional clock divider."
---

# `clkdiv` — Derives a clock as an arbitrary fraction of `clk`

## Overview

A fractional clock divider creates a non-drifting clock based off of any fractional ratio, to run a precise clock for weird ratios, letting us match any baud rate for our UART. It outputs `q` as the divided clock, using `b` and `c` as the fraction.
The ratio this clock divider is fq/fclk = c/2(b+c), where fq is the output clock and fclk is the input clock.

Some important notes on the parameters `b` and `c`:
- b AND c must both be > 0
- b >= c for correct behavior
- b + c <= 127

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |
| `b`  |     8      | b parameter for clkdiv |
| `c`  |     8      | c parameter for clkdiv |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `q`  |     1      | Output divided clock |

## Architecture Overview
http://wb6cxc.com/?p=158 provides a good overview of the math behind fractional clock dividers.

Uses an 8-bit accumulator register