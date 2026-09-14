# TinyTracer Documentation

TinyTracer is a ray-tracing graphics chip built for Tiny Tapeout. Start with
the [Introduction](introduction.md) for an overview of the architecture, then
use the pages below for the details of each module.

## Overview

- [`tt_um_tinytracer`](modules/tt_um_tinytracer.md): Top-level module for TinyTracer

## Encodings

- [Scene Encoding](modules/encoding/scene.md): Encoding for bounding volumes and primitives
- [Instruction Encoding](modules/encoding/instruction.md): Encoding for scalar and vector instructions
- [UART Frame Encoding](modules/encoding/uart_frame.md): Encoding for UART frames

## SRAM

- [`sram_control`](modules/sram/sram_control.md): SRAM Controller

## I/O

- [`io`](modules/io/io.md): UART wrapper that receives input commands and streams pixel data out
- [`uart`](modules/io/uart.md): Parses UART frames

## RTU

- [`rtu`](modules/rtu/rtu.md): Ray-tracing unit that carries out ray-tracing algorithm
- [`ray_generator`](modules/rtu/ray_generator.md): Generates primary and secondary rays
- [`intersection_unit`](modules/rtu/intersection_unit.md): Computes ray-object intersection
- [`shader_core`](modules/rtu/shader_core.md): Colours pixels based on ray-object intersection results and material metadata

## FUs

- [`fu_control`](modules/fu/fu_control.md): Top-level wrapper for functional units
- [`alu`](modules/fu/alu.md): Fixed-point ALU
- [`cordic`](modules/fu/cordic.md): CORDIC unit
- [`multiplier`](modules/fu/multiplier.md): Fixed-point multiplier
- [`rng`](modules/fu/rng.md): Xorshift-based random number generator
- [`invsqrt`](modules/fu/invsqrt.md): Computes inverse square roots

## Decode

- [`decode`](modules/decode/decode.md): Decodes messages between the RTU and FUs

## Register File

- [`reg_file`](modules/reg_file/reg_file.md): Register file for the FUs

## Accumulator

- [`accumulator`](modules/accumulator/accumulator.md): Buffer for the RTU to write pixel sample results to
