# TinyTracer Documentation

## Overview

- [Introduction](introduction.md)
- [`tt_um_tinytracer`](modules/tt_um_tinytracer.md): Top-Level Module for TinyTracer
- [`tinytracer_if`](modules/tinytracer_if.md): Interfaces between TinyTracer modules

## Encodings

- [Scene Encoding](encoding/scene.md): Encoding for bounding volumes and primitives
- [Instruction Encoding](encoding/instruction.md): Encoding for scalar and vector instructions
- [UART Frame Encoding](encoding/uart_frame.md): Encoding for UART frames

## SRAM

- [`sram_control`](modules/sram/sram_control.md): SRAM Controller

## I/O

- [`io`](modules/io/io.md): Communicates with external device to load scenes and render pixels
- [`uart`](modules/io/uart.md): UART transceiver

## RTU

- [`rtu`](modules/rtu/rtu.md): Instantiates Ray Generator, Intersection Unit, and Shader Core
- [`ray_generator`](modules/rtu/ray_gen/ray_generator.md): Generates primary and secondary rays
- [`rng`](modules/rtu/ray_gen/rng.md): Random number generator
- [`intersection_unit`](modules/rtu/intersection_unit.md): Computes ray-object intersection
- [`shader_core`](modules/rtu/shader_core.md): Colours pixels based on ray-object intersection results and material metadata

## FUs

- [`fu_control`](modules/fu/fu_control.md): Instantiates functional units
- [`alu`](modules/fu/alu.md): Fixed-point ALU
- [`cordic`](modules/fu/cordic.md): CORDIC Unit
- [`multiplier`](modules/fu/multiplier.md): Fixed-point multiplier

## Decode

- [`decode`](modules/decode/decode.md): Decodes messages between the RTU and FUs

## Register File

- [`reg_file`](modules/reg_file/reg_file.md): Register file for the FUs

## Accumulator

- [`accumulator`](modules/accumulator/accumulator.md): Buffer between the RTU and I/O Unit
