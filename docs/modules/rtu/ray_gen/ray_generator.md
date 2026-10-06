---
description: "Generates primary rays from the camera and secondary rays from hit surfaces."
---

# `ray_generator` — Generates primary and secondary rays

## Overview

This module generates primary and secondary rays to check for ray-object intersection. Primary rays originate from the camera origin, while secondary rays originate from the surface of an object that has been hit by a previous ray, in a direction chosen by the object's material. It instantiates the [`rng`](rng.md) submodule for random sampling.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `WLEN`  |     16      | Word length              |
| `PIX_W`  |     9      | Width of the pixel x and y counters |
| `DIM_WIDTH`  |     12      | Width of the image width from the I/O Unit |
| `SCRATCH_WORDS`  |     7      | Number of scratch registers |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |
| `start`  |     1      | Start signal from the Controller |
| `mode`  |     2      | 0: camera ray; 1: matte or ground bounce; 2: mirror bounce; 3: glass bounce. For a bounce, the Controller sets `mode` = `material` + 1 |
| `ray_o`  |     `vec3_t`      | $O$: ray origin, or the hit point after a surface hit |
| `ray_d`  |     `vec3_t`      | $D$: ray direction |
| `ray_n`  |     `vec3_t`      | $n$: surface normal, facing the incoming ray |
| `flip`  |     1      | Kept flip bit: the ray started inside the glass sphere |
| `scratch`  |     `scratch_t`      | Scratch registers, `SCRATCH_WORDS` $\times$ `WLEN` |
| `hdr_f`, `hdr_r`, `hdr_u`  |     `vec3_t`      | Camera vectors `F`, `R`, `U` (header registers) |
| `cam_z`  |     `WLEN`      | `CAM_Z`, the camera height (header register) |
| `pix_x`, `pix_y`  |     `PIX_W`      | Pixel being rendered (the Controller's counters) |
| `img_w`  |     `DIM_WIDTH`      | Image width, from [`render_if`](../../tinytracer_if.md#render_if); sets where the jitter bits start |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `done`  |     1      | One-cycle pulse in the cycle the new ray is written; $O$ and $D$ hold it from the next cycle |
| `o_we`  |     1      | Write `o_wdata` into $O$ |
| `o_wdata`  |     `vec3_t`      | New value of $O$ |
| `d_we`  |     1      | Write `d_wdata` into $D$ |
| `d_wdata`  |     `vec3_t`      | New value of $D$ |
| `scratch_we`  |     `SCRATCH_WORDS`      | Write `scratch_wdata` into each scratch word whose bit is high |
| `scratch_wdata`  |     `WLEN`      | New value of the scratch words |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| [`rtu_req_if.client`](../../tinytracer_if.md#rtu_req_if)  | Macro-op requests, with the operand values on `req_u` and `req_v`, and responses through the RTU request path |

### Registers

The RTU owns the shared header and ray state registers (see [RTU](../rtu.md#ray-state-registers)). The Ray Generator gets the ones it reads on its input ports and builds the values of its macro-op operands itself, from those registers, the last macro-op result (`req.resp_result`), LFSR bits, and constants. It drives them on `req.req_u` and `req.req_v` with the field write enables, and raises `req.req_resize` to resize $\mathbf{\vec{u}}$ before `M_NORM` (see [Handshakes](../rtu.md#handshakes)). It writes $O$, $D$, and scratch words through its write ports, only while it is active, and the RTU stores them at the end of the cycle.

It pulses the RNG's `req` in each cycle it writes a request field from `rand_num`.

## Architecture Overview

### Primary Rays

A screen sits in front of the camera. `F` points from the camera to its centre, `R` from the centre to the right edge, and `U` from the centre to the top edge (see [Scene Encoding](../../../encoding/scene.md#header)). A point on the screen is $F + aR + bU$, with $a$ from -1 (left) to +1 (right) and $b$ from +1 (top) to -1 (bottom). The primary ray has origin $O$ = (0, 0, `CAM_Z`) and direction $D$ = resize($F + aR + bU$).

$a$ and $b$ are DIR numbers made by placing bits, with no adder. For a 512-pixel-wide image, one pixel is $2 / 512 \times 16384$ = 64 DIR steps, so the pixel bits start at bit 6 and 6 random bits below them move each sample to a different point inside the pixel (jitter):

| Bits | [15] | [14] | [13:6] | [5:0] |
|----|:----:|:----:|:----:|:----:|
| $a$ | $\overline{x_8}$ | $\overline{x_8}$ | $x[7:0]$ | random |
| $b$ | $y_8$ | $y_8$ | $\overline{y[7:0]}$ | random |

$x - 256$ in two's complement is $x$ with bit 8 inverted, and $255 - y$ is $y$ with bits 7-0 inverted. For a narrower image of width $W$ (a power of 2), the pixel bits move up, and there are $15 - \log_2 W$ random bits.

| Step | Macro-ops | Cycles |
|----|----|:----:|
| $aR = a \times R$, $bU = b \times U$ | 2 $\times$ `M_SCAL_VEC` | 14 |
| $F + aR + bU$ | 2 $\times$ `M_VADD` | 14 |
| $D$ = resize($F + aR + bU$) | resize pre-shift, `M_NORM` | 65 |
| $O$ = (0, 0, `CAM_Z`) | none | 0 |
| Total | | 93 |

To resize a vector to length 1, the Ray Generator writes it into $\mathbf{\vec{u}}$ with `req_resize` high. The RTU request path first shifts all three parts so that the largest is 0.5 to 1 as a DIR number (see [Number Formats](../../../encoding/number_format.md#resize-pre-shift)), then sends one `M_NORM` (65 cycles). `F` has length 1 and `R` and `U` at most 1, so $F + aR + bU$ is at most 1.73 long.

### Secondary Rays

After a surface hit below the bounce limit, the Ray Generator picks the new direction from the material, which the Controller gives it in `mode`, using the hit point and surface normal $n$ that the Intersection Unit left in $O$ and $n$. $n$ always faces the incoming ray.

- __Matte and ground__: $D$ = resize($n + r$), where $r$ is a random unit vector. $n + r$ lies on a sphere of radius 1 resting on the surface, so $D$ always leaves the surface and favours directions near $n$. If $n + r$ = 0, the leading-one finder of the resize pre-shift would find no 1 bit, so the Ray Generator checks the `M_VADD` result and, if it is 0, writes $D = n$ instead of sending `M_NORM`
- __Mirror__: $D - 2(D \cdot n)n$. No random part and no resize: the length stays 1
- __Glass__ (spheres only, index of refraction 1.5): $\cos\theta = -(D \cdot n)$ and $k = 1 - \eta^2(1 - \cos^2\theta)$, where $\eta$ = 1/1.5 = 0.667 entering the sphere and 1.5 leaving it (the flip bit says the ray started inside). The ray reflects, $D + 2\cos\theta \, n$, if $k < 0$ (total internal reflection) or if 8 random bits are below $0.04 + 0.96(1 - \cos\theta)^5$ (Schlick's approximation). Otherwise it refracts: resize($\eta D + (\eta\cos\theta - \sqrt{k})\,n$)

The random unit vector $r$ uses 18 random bits and no loop. $z$ is 8 random bits, sign-extended into a DIR number (-0.992 to 0.992; -128 is read as -127). $w$ is 8 random bits, 0 to 0.996, and the heading is $\varphi = w \times \pi/2$ (0 to 90°). Picking $z$ and $\varphi$ evenly gives every direction the same chance. Then $\rho = \sqrt{1 - z^2}$ and $r = (\pm\rho\cos\varphi, \pm\rho\sin\varphi, z)$. `M_COS` computes $u_1\cos(v_1)$, so it gives $\rho\cos\varphi$ and $\rho\sin\varphi = \rho\cos(\varphi - \pi/2)$ directly, with $u_1 = \rho$. The two signs come from 2 more random bits, which the Ray Generator applies by XOR as it builds the operands, and it places $z$ in the request by wiring. Both `M_COS` angles stay within the CORDIC range of $\pm$99.8°.

Every material then moves the new origin off the surface, $O$ = hit point + 0.031 $\times n$ (4 POS steps), so that rounding cannot make the new ray hit the same surface again at $t \approx 0$. A refracted glass ray moves into the glass instead, $O$ = hit point - 0.031 $\times n$.

| Material | Steps | Cycles |
|----|----|:----:|
| Matte, ground | $\varphi$ (`M_MUL`, 3); $\rho$ (`M_MUL`, `M_SUB`, `M_SQRT`, 31); $\rho\cos\varphi$, $\rho\sin\varphi$ (2 $\times$ `M_COS`, `M_SUB`, 43); $n + r$ (`M_VADD`, 7); resize (`M_NORM`, 65) | 149 |
| Mirror | $D \cdot n$ (`M_DOT`, 11); $2(D \cdot n)$ (`M_ADD`, 3); $D - 2(D \cdot n)n$ (`M_SCAL_VEC`, `M_VSUB`, 14) | 28 |
| Glass | $\cos\theta$ (14); $k$ (15); Schlick share (18); reflect or refract (2 compares, 6); reflect (17) or refract (6 macro-ops and a resize, 117) | 70 (reflect), 170 (refract) |
| Push off, every material | `M_SCAL_VEC`, `M_VADD` | 14 |
