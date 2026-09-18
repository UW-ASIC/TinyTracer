# `reg_file` — Register file for the FUs

## Overview

This module is used to store initial data for micro-ops to operate on as well as intermediate results from micro-ops.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `WLEN`  |     16      | Word length              |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| `reg_file_if`  | Single read/write port |

## Architecture Overview