---
description: "Finds the closest sphere, triangle, or ground hit along a ray segment, using bounding volumes to skip objects, and returns the hit point and surface normal."
---

# `intersection_unit` — Computes ray-object intersection

## Overview

This module finds the first thing a ray segment hits and, for that hit only, computes the hit point and surface normal. It tests every bounding volume, the spheres and triangles of every bounding volume the ray can reach, and then the ground plane. Intersection calculations are determined by the primitive type, with ray-sphere intersection using the quadratic formula and ray-triangle intersection using the Möller-Trumbore method.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `WLEN`  |     16      | Word length              |
| `MACRO_W`  |     102     | Macro operation width             |
| `ADDR_WIDTH`  |     9     | SRAM address width             |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |
| `start`  |     1      | Start signal from the Controller |
| `mode`  |     2      | 0: search for the closest hit; 1: read the closest object's colour, strength, and material; 2: compute the hit point and surface normal of the closest hit |

### Outputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `done`  |     1      | One-cycle pulse: the mode's work is finished |
| `hit_kind`  |     `hit_kind_t`      | Result of the search (`HIT_SKY` = 0, `HIT_GROUND` = 1, `HIT_OBJECT` = 2); valid with `done` in mode 0 |
| `material`  |     `mat_type_t`      | Material of the closest object; valid with `done` in mode 1 |

### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| [`rtu_req_if.client`](../tinytracer_if.md#rtu_req_if)  | Macro-op requests and responses through the RTU request path |
| [`sram_rd_if.client`](../tinytracer_if.md#sram_rd_if)  | SRAM reads, connected to the RTU's SRAM port while the Intersection Unit is active |

### Registers

The Intersection Unit works on the RTU's shared registers (see [RTU](rtu.md#ray-state-registers)), sends its macro-ops through the RTU request path, and reads the SRAM while it is active (see [Handshakes](rtu.md#handshakes)). The signals it uses to select operand sources and to write registers are not defined yet.

| Access | Registers |
|----|----|
| Reads | $O$, $D$; `BV_NUM` (header registers); SRAM words |
| Writes | best $t$, best address, hit kind; kept test values; material, the closest object's colour and glow strength; $O$ (hit point); $n$; scratch; BV address, BVs left, object address, objects left |

## Architecture Overview

### Search

The search starts with best $t$ = 255.99 and no best hit, and runs the following loop:

1. For each bounding volume $i$ = 0 to `BV_NUM` - 1, read `w1`-`w4` (radius and centre, 8 cycles) and run the bounding volume test
2. If the ray can reach the bounding volume, read its `w0` (2 cycles): the address and number of its primitives. Otherwise skip to the next bounding volume, 5 words on
3. For each primitive, read `w0`, whose `TYPE` bit selects the sphere or triangle test. If the test hits at $t$ < best $t$, keep $t$, the primitive's address, and its kept test values. The next primitive starts 7 (sphere) or 12 (triangle) words on
4. If no primitive was hit and the ray points down ($D_z$ < 0), test the ground: $t = -O_z \div D_z$, one `M_DIV` with $-O_z$ made by the sign flip. If the division clamps ($t$ = `16'h7FFF`), the ground is too far away
5. The hit kind is object, ground, or sky (nothing hit, the ray points up, or the ground is too far away). It is written to the ray state registers and output on `hit_kind` with `done`. For the ground, the material is set to matte

Every bounding volume the ray can reach is searched, since bounding volumes can overlap and the closest bounding volume does not always hold the closest hit. A skipped bounding volume costs no primitive reads. The ground is tested only when no primitive was hit, which is correct because the host keeps every object at z $\ge$ 0: along a ray that goes down, any point of an object comes before the ground.

Each test stops at its first failed check. The squares in the sphere and bounding volume tests, and the products in the triangle test, are computed after the size shift $K$ (see [Number Formats](../../encoding/number_format.md#size-shift-k)). $t \le 0.0156$ (2 POS steps) counts as behind the ray origin.

### Bounding Volume Test

The test decides whether the ray can reach a bounding volume with centre $C$ and radius $r$. With $\mathrm{to\_centre} = C - O$, the distance along the ray to the point $P$ closest to $C$ is $\text{along} = \mathrm{to\_centre} \cdot D$ (which needs $\lvert D \rvert$ = 1), and $\text{offset} = P - C = \text{along} \times D - \mathrm{to\_centre}$. The checks, in order:

1. $\lvert\mathrm{to\_centre}_s\rvert^2 < r_s^2$: the ray starts inside, so it can reach. Every bounce starts inside its own bounding volume
2. $\text{along} < 0$: the centre is behind the origin, so skip
3. $\lvert\text{offset}_s\rvert^2 < r_s^2$: reach, otherwise skip

| Step | Macro-ops | Cycles |
|----|----|:----:|
| Read `w1`: radius; $K$ and $r_s$ | SRAM | 2 |
| $r_s^2$ | `M_MUL` | 3 |
| Read `w2`-`w4`: centre | SRAM | 6 |
| $\mathrm{to\_centre}$ | `M_VSUB` | 7 |
| $\text{along}$ | `M_DOT` | 11 |
| $\lvert\mathrm{to\_centre}_s\rvert^2$; check 1 | `M_DOT`, `M_LT` | 14 |
| check 2 | `M_LT` | 3 |
| $\text{offset}_s$ | `M_SCAL_VEC`, `M_VSUB` | 14 |
| $\lvert\text{offset}_s\rvert^2$; check 3 | `M_DOT`, `M_LT` | 14 |
| If reached, read `w0` | SRAM | 2 |

A bounding volume test takes 45 to 76 cycles: 45 if the ray starts inside, 46 if the centre is behind, 74 if skipped at check 3, and 76 if reached at check 3.

### Sphere Test

The sphere test uses the same $\mathrm{to\_centre}$, $\text{along}$, and $\text{offset}$. If $\lvert\text{offset}\rvert \ge r$, it misses. Otherwise the ray crosses the sphere half a chord before and after $P$, with $\text{half} = \sqrt{r^2 - \lvert\text{offset}\rvert^2}$, and the entry point is at $t = \text{along} - \text{half}$. If the entry point is behind the origin, the test tries the exit point, $t = \text{along} + \text{half}$: the ray starts inside the sphere (glass), or, if that is also behind the origin, the sphere is behind the ray and it misses.

| Step | Macro-ops | Cycles |
|----|----|:----:|
| Read `w0` and `w3`-`w6` | SRAM | 10 |
| $\mathrm{to\_centre}$ | `M_VSUB` | 7 |
| $\text{along}$ | `M_DOT` | 11 |
| $\text{offset}$ | `M_SCAL_VEC`, `M_VSUB` | 14 |
| $\lvert\text{offset}_s\rvert^2$, $r_s^2$ | `M_DOT`, `M_MUL` | 14 |
| $\lvert\text{offset}_s\rvert^2 < r_s^2$? | `M_LT` | 3 |
| $\text{half}$, shifted back by $K$ | `M_SUB`, `M_SQRT` | 28 |
| $t = \text{along} - \text{half}$; $t \le 0.0156$? | `M_SUB`, `M_LT` | 6 |
| Only if behind: $t = \text{along} + \text{half}$; $t \le 0.0156$? | `M_ADD`, `M_LT` | 6 |
| $t$ < best $t$? | `M_LT` | 3 |

A sphere test takes 59 cycles if it misses at the first compare, 96 for a hit from outside, 99 if the sphere is behind the ray, and 102 for a hit from inside. A new best sphere hit keeps $\text{offset}_s$, $\text{half}_s$, $r_s$, and a flip bit that is 1 if the ray starts inside.

### Triangle Test

A point of the triangle's plane is $v_0 + \alpha e_1 + \beta e_2$, and it is inside the triangle when $\alpha \ge 0$, $\beta \ge 0$, and $\alpha + \beta \le 1$. The test runs in four stages and stops at the first failed check:

| Stage | Computes | Misses if | Cycles |
|----|----|----|:----:|
| 1 | Read `w0` and `w3`-`w11` (20 cycles); $K$ from the edges; $\mathrm{to\_corner} = v_0 - O$; $\text{along} = \mathrm{to\_corner} \cdot D$; $\text{slid} = \text{along} \times D - \mathrm{to\_corner}$, shifted by $K$ | $\lvert\text{slid}_s\rvert^2 > 225$ | 66 |
| 2 | Re-read $e_2$, $e_1$, shifted by $K$; $P = D \times e_2$; $\det = e_1 \cdot P$; $\alpha_{top} = \text{slid} \cdot P$; if $\det < 0$, negate $\det$ and $\alpha_{top}$ (flip bit = 1) | $\det \le 0$, $\alpha_{top} < 0$, or $\alpha_{top} > \det$ | 60 (66 flipped) |
| 3 | Re-read $e_1$; $Q = \text{slid} \times e_1$; $\beta_{top} = D \cdot Q$, negated if flipped | $\beta_{top} < 0$ or $\alpha_{top} + \beta_{top} > \det$ | 40 (43 flipped) |
| 4 | Re-read $e_1$, $e_2$; $\alpha = \alpha_{top} \div \det$; $\beta = \beta_{top} \div \det$; $t = \text{along} + \alpha(e_1 \cdot D) + \beta(e_2 \cdot D)$ | $t \le 0.0156$ | 90 |

* $\text{slid}$ is the vector from $v_0$ to the point of the ray closest to $v_0$. After the size shift, every point of the triangle is within 13.9 of $v_0$, so a ray that passes more than 15 from $v_0$ misses. Using $\text{slid}_s$ instead of $O - v_0$ keeps the later products below 256
* Stages 2 and 3 check $0 \le \alpha_{top}$, $0 \le \beta_{top}$, and $\alpha_{top} + \beta_{top} \le \det$ without dividing. $\det < 0$ means the ray meets the back side of the triangle
* Stage 4 uses $(v_0 - O) \cdot D = \text{along}$, from $O + tD = v_0 + \alpha e_1 + \beta e_2$ dotted with $D$
* Seven values are kept in the scratch registers between macro-ops: $\text{slid}_s$ (3 parts), $\text{along}$, $\det$, $\alpha_{top}$, and $\beta_{top}$. $P$ and $Q$ each feed the next request directly; $P$ stays in the request register for the second dot product
* A new best triangle hit keeps its flip bit and $K$

On the demo scene, a triangle test takes 144 cycles on average, since most tests stop in stage 1 or 2.

### Closest Hit

After the search, the Controller runs the Intersection Unit again for the closest hit only (see [RTU](rtu.md#controller)):

- __Mode 1__, for an object: read `w0`-`w2` (6 cycles) into the ray state registers: the colour and glow strength for the Shader Core, and the material, which is also output on `material` with `done`. The Controller uses it to skip mode 2 for a glowing object
- __Mode 2__, unless the object glows or the bounce limit is reached: compute the hit point and surface normal $n$ from the values the test kept, so the test never runs a second time. The hit point $O + tD$ is written into $O$

- __Sphere__: $n = (\text{offset}_s - \text{half}_s \times D) \div r_s$. The hit point is half a chord before $P$, so the hit point minus $C$ is $\text{offset} - \text{half} \times D$, which has length exactly $r$, so three divisions (`M_SPHERE_NORM`) give length 1 without a resize. If the ray started inside (glass), the hit is the exit point: $n$ uses $\text{offset}_s + \text{half}_s \times D$ and is then negated to face the ray
- __Triangle__: the RTU loads `w3`-`w8` (the edges), shifted by the kept $K$, into the request's $\mathbf{\vec{u}}$ and $\mathbf{\vec{v}}$, and $n$ = resize($\mathbf{\vec{u}} \times \mathbf{\vec{v}}$). The flip bit picks which edge goes where, so that $n$ faces the ray: $e_1 \rightarrow \mathbf{\vec{u}}$, $e_2 \rightarrow \mathbf{\vec{v}}$ on the front side, and the reverse on the back side, since $\det = -D \cdot (e_1 \times e_2)$
- __Ground__: $n$ = (0, 0, 1)

| Hit | Steps | Cycles |
|----|----|:----:|
| Sphere | mode 1: read `w0`-`w2` (6); mode 2: hit point (`M_SCAL_VEC`, `M_VADD`, 14); $\text{half}_s \times D$ (`M_SCAL_VEC`, 7); subtract (`M_VSUB`, 7); $n$ (`M_SPHERE_NORM`, 57) | 91 (98 inside glass) |
| Triangle | mode 1: read `w0`-`w2` (6); mode 2: hit point (14); read `w3`-`w8` (12); $\mathbf{\vec{u}} \times \mathbf{\vec{v}}$ (`M_CROSS`, 14); resize (`M_NORM`, 65) | 111 |
| Ground | mode 2: hit point (14); $n$ = (0, 0, 1) (constant) | 14 |
