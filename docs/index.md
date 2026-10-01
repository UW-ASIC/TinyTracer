# TinyTracer Documentation

## Overview

- [Introduction](introduction.md)
- [`tt_um_tinytracer`](modules/tt_um_tinytracer.md): Top-Level Module for TinyTracer
- [`tinytracer_if`](modules/tinytracer_if.md): Interfaces between TinyTracer modules

## Encodings

- [Number Formats](encoding/number_format.md): Fixed-point formats for positions, directions, and colours
- [Scene Encoding](encoding/scene.md): Memory map, header, bounding volumes, and primitives
- [Instruction Encoding](encoding/instruction.md): Encoding for scalar and vector instructions
- [UART Frame Encoding](encoding/uart_frame.md): Encoding for UART frames

## SRAM

- [`sram_control`](modules/sram/sram_control.md): SRAM Controller
- [`scene_sram`](modules/sram/scene_sram.md): Scene SRAM

## I/O

- [`io`](modules/io/io.md): Communicates with external device to load scenes and render pixels
- [`uart`](modules/io/uart.md): UART transceiver
- [`clkdiv`](modules/io/clkdiv.md): Derives a clock as an arbitrary fraction of `clk`

## RTU

- [`rtu`](modules/rtu/rtu.md): Instantiates Ray Generator, Intersection Unit, and Shader Core
- [`ray_generator`](modules/rtu/ray_gen/ray_generator.md): Generates primary and secondary rays
- [`rng`](modules/rtu/ray_gen/rng.md): Random number generator
- [`intersection_unit`](modules/rtu/intersection_unit.md): Computes ray-object intersection
- [`shader_core`](modules/rtu/shader_core.md): Colours pixels based on ray-object intersection results and material metadata

## EXU

- [`exu`](modules/exu/exu.md): Instantiates Decode Unit, Register File, and Functional Units
- [`decode`](modules/exu/decode.md): Decodes messages between the RTU and FUs
- [`reg_file`](modules/exu/reg_file.md): Register file for the FUs
- [`fu_control`](modules/exu/functional_units/fu_control.md): Instantiates functional units
- [`alu`](modules/exu/functional_units/alu.md): Fixed-point ALU
- [`cordic`](modules/exu/functional_units/cordic.md): CORDIC Unit
- [`multiplier`](modules/exu/functional_units/multiplier.md): Fixed-point multiplier

## Accumulator

- [`accumulator`](modules/accumulator/accumulator.md): Buffer between the RTU and I/O Unit
