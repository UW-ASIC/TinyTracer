---
description: "The UART runs on a separate clock to achieve a desired baud rate, derived from the system clock. To achieve this, we use a fractional clock divider."
---

# `clkdiv` — Derives a clock as an arbitrary fraction of `clk`

## Overview

A fractional clock divider creates a non-drifting clock based off of any fractional ratio, to run a precise clock for weird ratios, letting us match any baud rate for our UART. It outputs `q` as the divided clock, using `b` and `c` as the fraction.
The ratio this clock divider is fq/fclk = c/2(c-b), where fq is the output clock and fclk is the input clock.

Some important notes on the parameters `b` and `c`:
- b > 0 AND c < 0
- b >= -c for correct behavior
- b - c <= 127

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

## Baud Rates

The UART needs `q` at 16 $\times$ the baud rate, so with a 25 MHz `clk`, $16 \times \text{baud} = 25\text{ MHz} \times c / 2(c - b)$.

| Baud rate | b | c | `q` | Actual baud rate | Error |
|:----:|:----:|:----:|:----:|:----:|:----:|
| 115,200 | 104 | -18 | 1.844 MHz | 115,266 | +0.06% |
| 230,400 | 43 | -18 | 3.689 MHz | 230,533 | +0.06% |

Since b $\ge$ -c, the fastest setting is b = -c, which gives `q` = 25 MHz / 4 = 6.25 MHz, or 390,625 baud. So 230,400 is the fastest standard baud rate, and 460,800 is out of reach. Which rate TinyTracer uses is still open. At 115,200 baud the UART slows a 512 $\times$ 512 render at 8 samples per pixel by about 21%, since many sky and ground pixels render faster than the 347 µs it takes to send a pixel; at 230,400 baud it slows it by about 3%, and at 32 samples per pixel it does not slow it at all.
