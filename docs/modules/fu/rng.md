# `rng` — Random number generator

## Overview

This module is a Random Number Generator using a Xorshift linear feedback shift register (LFSR).

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `WLEN`  |     16      | Word length              |
| `SEED` | `16'hACE1` | RNG seed |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| `fu_if`  | Micro-op request and response channel from FU Control |

## Architecture Overview