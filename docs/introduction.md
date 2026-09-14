# Introduction

## Introduction to TinyTracer

TinyTracer is a small ray-tracing graphics chip written in Verilog by the
University of Waterloo ASIC Design Team and built through
[Tiny Tapeout](https://tinytapeout.com). A host sends a scene description over
UART, the chip renders it, and the finished pixels stream back over the same
UART link. Everything is computed in 16-bit fixed point, and the whole design
fits in a 4x2 Tiny Tapeout tile.

The rendering parameters are fixed at build time in
`src/include/tinytracer_defs.vh`:

| Parameter          | Value                                        |
| ------------------ | -------------------------------------------- |
| Image size         | 64 x 64 pixels                               |
| Samples per pixel  | 8                                            |
| Maximum ray bounces| 10                                           |
| Colour depth       | 8 bits per channel (24-bit RGB)              |
| Number format      | Q8.8 signed fixed point, range -128 to +128  |
| Primitives         | Spheres and triangles                        |
| Materials          | Diffuse, reflective, dielectric, emissive    |
| Scene memory       | 512 x 16-bit SRAM                            |
| System clock       | 50 MHz                                       |
| UART               | 115 200 baud, RX on `ui[3]`, TX on `uo[4]`   |

## Architectural Overview

TinyTracer is organised as a chain of blocks that hand work to each other over
valid/ready channels. The ray-tracing unit decides *what* to compute, and a
small functional-unit cluster does the arithmetic.

```text
 UART RX ──▶ ┌──────┐ ──▶ ┌────┐ ◀── pixels ── ┌─────────────┐
             │ uart │     │ io │               │ accumulator │
 UART TX ◀── └──────┘ ◀── └────┘               └─────────────┘
                            │ scene                  ▲ samples
                            ▼ writes                 │
                      ┌──────────────┐  reads  ┌─────────────────────┐
                      │ sram_control │ ◀─────▶ │ rtu                 │
                      │  512 x 16b   │         │  ray_generator      │
                      └──────────────┘         │  intersection_unit  │
                            ▲                  │  shader_core        │
                            │ LUT reads        └─────────────────────┘
                            │                     │ macro-ops   ▲ results
                            │                     ▼             │
                            │                  ┌──────────────────────┐
                            │                  │ decode  ◀─▶ reg_file │
                            │                  └──────────────────────┘
                            │                     │ micro-ops   ▲ done
                            │                     ▼             │
                            │                  ┌─────────────────────┐
                            └──────────────────│ fu_control          │
                                               │  alu   multiplier   │
                                               │  cordic   rng       │
                                               └─────────────────────┘
```

- **I/O** ([`uart`](modules/io/uart.md), [`io`](modules/io/io.md)) receives
  UART frames, writes scene objects into SRAM, starts a render, and streams
  finished pixels back out.
- **SRAM** ([`sram_control`](modules/sram/sram_control.md)) arbitrates one
  512-word memory between scene writes from I/O, scene reads from the RTU, and
  lookup-table reads from the CORDIC unit.
- **Ray-tracing unit** ([`rtu`](modules/rtu/rtu.md)) walks the scene for every
  sample. Its [`ray_generator`](modules/rtu/ray_generator.md) produces primary
  rays from the camera and secondary rays after each hit,
  [`intersection_unit`](modules/rtu/intersection_unit.md) tests a ray against
  a sphere or triangle, and [`shader_core`](modules/rtu/shader_core.md) turns
  hit results and material metadata into a colour sample.
- **Decode** ([`decode`](modules/decode/decode.md)) breaks each vector-level
  macro-op from the RTU into a sequence of scalar micro-ops, using
  [`reg_file`](modules/reg_file/reg_file.md) as scratch space.
- **Functional units** ([`fu_control`](modules/fu/fu_control.md)) route each
  micro-op to the [`alu`](modules/fu/alu.md) (add, subtract, compare), the
  [`multiplier`](modules/fu/multiplier.md), the [`cordic`](modules/fu/cordic.md)
  unit (divide, square root, cosine, reciprocal), or the
  [`rng`](modules/fu/rng.md).
- **Accumulator** ([`accumulator`](modules/accumulator/accumulator.md))
  averages the samples of each pixel and forwards the finished pixel to I/O.
- **Top level** ([`tt_um_tinytracer`](modules/tt_um_tinytracer.md)) wires the
  blocks together and maps them onto the Tiny Tapeout pins.

## Rendering a Frame

1. The host sends the scene over UART. `io` parses each object frame and writes
   it to SRAM through `sram_control`.
2. The host sends a render command. `io` pulses `render` to the RTU.
3. For every pixel and every sample, the RTU generates a ray, intersects it with
   the scene objects read from SRAM, shades the hit, and follows secondary rays
   until the ray escapes, hits an emissive surface, or runs out of bounces.
4. Vector maths inside the RTU is expressed as macro-ops such as dot product,
   cross product and normalisation. `decode` expands each one into scalar
   micro-ops that the functional units execute one at a time.
5. Each finished colour sample goes to the accumulator. Once a pixel has all of
   its samples, the averaged colour is handed to `io` and transmitted.

## Target Use Cases

- A complete, readable example of how a ray tracer maps onto a tiny amount of
  silicon, with no floating point and a single shared memory.
- A Tiny Tapeout design that can be exercised from any host with a UART.
- A base for experiments: swap a functional unit, change the fixed-point
  format, or add a primitive type without touching the rest of the pipeline.

## TinyTracer for Non-Experts

### What Is TinyTracer?

Ray tracing is how film and modern game graphics produce realistic lighting.
For each pixel of the picture, the computer shoots an imaginary ray out of a
camera, finds the first object it hits, and works out how light would bounce
off that surface. TinyTracer is a chip that does exactly this, but small enough
to be manufactured as a student project.

### Why Is TinyTracer Interesting?

Ray tracing on a desktop computer leans on fast floating-point hardware and
lots of memory. TinyTracer has neither. It uses 16-bit fixed-point numbers,
a 1 KB memory, and a handful of arithmetic units, and it renders one sample
at a time. Seeing a full rendering pipeline squeezed into that budget shows
which parts of the algorithm are essential and which are luxuries.
