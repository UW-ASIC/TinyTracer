---
description: "Fixed-point number formats TinyTracer uses for positions, directions, colours, and integers, and how the functional units combine them."
---

# Number Formats

## Overview

TinyTracer has no floating point. Every number is a 16-bit two's complement integer, the *raw* value, read with a fixed binary point. Qm.n means m bits before the binary point (sign included) and n bits after it, so the value is raw $\div 2^n$.

TinyTracer uses two 16-bit fixed-point formats: POS for positions and distances, and DIR for directions. Two formats are needed because a single format cannot hold both a scene that is hundreds of units across and a unit vector with enough fractional bits.

## Formats

| Format | Bits | Range | Step | Used for |
|----|:----:|:----:|:----:|----|
| POS (Q9.7) | 16 signed | -256 to 255.99 | 1/128 | Positions (ray origin, centres, triangle corner), radii, triangle edges, hit distance $t$, intermediate distances of the intersection tests, camera height |
| DIR (Q2.14) | 16 signed | -2 to 1.99994 | 1/16384 | Directions (ray direction $D$, surface normal $n$, camera vectors $F$, $R$, $U$), screen coordinates, random vectors, angles in radians, cosines, triangle coordinates $\alpha$, $\beta$, reciprocals of lengths, constants |
| Colour | 8 unsigned | 0 to 255 | 1 | Object, sky, and ground colours; attenuation (255 = 1.0) |
| Strength (Q4.10) | 14 unsigned | 0 to 15.99 | 1/1024 | Glow strength (1024 = 1.0) |
| Sample | 12 unsigned | 0 to 4080 | 1 | Sample colour per channel, from the Shader Core |
| Sum | 17 unsigned | 0 to 130560 | 1 | Accumulator sum per channel (up to 32 samples) |
| Pixel | 8 unsigned | 0 to 255 | 1 | Pixel colour per channel, sent over UART |

Integer fields: SRAM address 9 bits, object count 7 bits, size shift $K$ 5 bits signed, pixel x and y 9 bits each, samples per pixel 3 bits ($\log_2$), sample counter 5 bits, bounce counter 4 bits, material 2 bits, primitive type 1 bit, compare flag 1 bit.

## Combining Formats

A 16 $\times$ 16 multiply gives a 32-bit product. The multiplier shifts it right with rounding to get 16 bits. The amount of the shift sets the format of the result, and is selected by the `FMT` bit of the macro-op (see [Instruction Encoding](instruction.md)).

Every add, subtract, multiply, shift, and divide clamps: a result that does not fit in 16 bits is replaced by the largest (`16'h7FFF`) or smallest (`16'h8000`) 16-bit value. For POS, `16'h7FFF` is 255.99.

| Operands | Rule | Result | Examples |
|----|----|----|----|
| POS $\times$ POS | shift right 7 (`FMT` = 0) | POS | squared lengths, $r^2$, triangle determinant |
| POS $\times$ DIR | shift right 14 (`FMT` = 1) | POS | distance along a ray, $t \times D$ |
| DIR $\times$ DIR | shift right 14 (`FMT` = 1) | DIR | $a \times R$, $D \cdot n$ |
| $a \div b$ | $(a \ll 14) \div b$ | POS $\div$ POS $\rightarrow$ DIR, POS $\div$ DIR $\rightarrow$ POS, DIR $\div$ DIR $\rightarrow$ DIR | triangle $\alpha$, $\beta$; sphere normal; ground distance; $1.0 \div$ length |
| $\sqrt{a}$ | two modes, selected by `FMT` | POS $\rightarrow$ POS (`FMT` = 0), DIR $\rightarrow$ DIR (`FMT` = 1) | sphere half chord; glass; matte bounce |
| $a \cos b$ | $b$ in radians, $\lvert b \rvert \le 1.743$ (about 99.8°) | same format as $a$ | matte bounce ($\rho\cos\varphi$, $\rho\sin\varphi$) |
| $a + b$, $a - b$, compare | none | same format on both sides | $t$ = along + $\alpha (e_1 \cdot D) + \beta (e_2 \cdot D)$ |
| sign flip | XOR every bit with a control bit, no adder | $-a$ - 1 step | random signs in the matte bounce, $-O_z$ for the ground |
| colour | attenuation $\times$ colour $\gg 8$; $\times$ strength $\gg 10$ | Colour, Sample | attenuation, sample colour (see [Shader Core](../modules/rtu/shader_core.md)) |
| samples to pixel | sum $\gg \log_2 s$, clamp to 255 | Pixel | [Accumulator](../modules/accumulator/accumulator.md) |

The colour multiplies need shifts of 8 and 10, which the 1-bit `FMT` field cannot select. This is still open (see [Instruction Encoding](instruction.md)).

## Keeping Values in Range

Every number the chip computes must fit in its format. Each case below is kept in range by a rule:

| Value | Largest size | Why it fits |
|----|----|----|
| positions | below 256 per part | The host keeps the scene within $\pm$256 and moves it so the camera is at x = y = 0 |
| differences of two points (centre minus ray origin, triangle corner minus ray origin) | below 256 per part | The host keeps any two points the chip subtracts less than 256 apart per part |
| unit vectors $D$, $n$, $F$ | parts -1 to 1 | Length 1 |
| $R$, $U$ | length $\le$ 1 | Length $\tan(\text{fov} / 2)$, and the field of view is at most 90° |
| $F + aR + bU$ | length $\le \sqrt{3}$ = 1.73 | $F$, $R$, $U$ are orthogonal and $\lvert a \rvert, \lvert b \rvert \le 1$; resized to length 1 straight after |
| distance $\times$ unit vector | below 256 | The vector has length 1, so the product is never longer than the distance |
| squared lengths in the sphere and bounding volume tests | $r_s^2$: 64 to 256 | The size shift $K$ makes the radius 8 to 16 first; a larger squared offset clamps, and the compare against $r_s^2$ still gives the right answer |
| triangle determinant and $\alpha$, $\beta$ numerators | $\le$ 208 | The size shift $K$ makes the largest edge part 4 to 8 first |

## Shifts in the RTU Request Path

The RTU applies two kinds of shift to operands on their way into a macro-op request. Both are wiring and a leading-one finder, so they take 0 cycles (see [RTU](../modules/rtu/rtu.md)).

### Size Shift $K$

The sphere and bounding volume tests square the radius and the offset of the ray from the centre. POS stops at 256, so a sphere with $r$ = 20 would give $r^2$ = 400 and clamp; a small sphere with $r$ = 1.5 gives $r^2$ = 2.25, which keeps few correct bits. So before squaring, the RTU scales the object by a power of 2, $2^{-K}$, so that its radius is 8 to 16 and $r^2$ is 64 to 256. The name of a value after the shift ends in $s$: $r_s$ is the radius shifted by $K$.

* __Spheres and bounding volumes__: $K$ = (index of the highest 1 bit of the raw radius) - 10. Every radius from 8 to 16 has a raw value of 1024 to 2047, whose highest 1 bit is bit 10.
* __Triangles__: $K$ = (index of the highest 1 bit of the largest raw edge part) - 9, so that the largest edge part is 4 to 8 and every edge is at most $8\sqrt{3}$ = 13.9 long.
* $K$ is 5 bits, signed. $K > 0$ shifts right ($\div 2^K$), $K < 0$ shifts left ($\times 2^{-K}$).
* Every value that is compared with a shifted value is shifted by the same $K$, so the compare gives the same answer. A result that keeps the scale (the sphere half chord) is shifted back by $K$.

| Radius $r$ | raw = $r \times$ 128 | Highest 1 bit | $K$ | $r_s$ | $r_s^2$ |
|:----:|:----:|:----:|:----:|:----:|:----:|
| 1.5 | 192 | 7 | -3 | 12 | 144 |
| 6 | 768 | 9 | -1 | 12 | 144 |
| 16.74 | 2143 | 11 | 1 | 8.375 | 70.14 |
| 40 | 5120 | 12 | 2 | 10 | 100 |

### Resize Pre-Shift

Before a vector is sent to `M_NORM` (resize to length 1), the RTU shifts all three parts by the same amount so that the largest part is 0.5 to 1 when read as DIR. The shift also turns a POS vector into a DIR vector. The length is then 0.5 to 1.73, so $1 \div$ length is 0.58 to 2; a 2 clamps to 1.99994, which is half a step short and too small to matter. If all three parts are 0, the leading-one finder finds no 1 bit; the matte bounce uses this case (see [Ray Generator](../modules/rtu/ray_gen/ray_generator.md)).
