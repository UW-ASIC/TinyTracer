---
description: "How TinyTracer lays out a scene in SRAM: the header, bounding volumes, and sphere and triangle primitives."
---

# Scene Encoding

* The SRAM holds 512 16-bit words. The host writes the whole scene with OBJECT messages before a render (see [UART Frame Encoding](uart_frame.md)); the chip only reads it while rendering
* Positions, radii, and edges are POS numbers and the camera vectors are DIR numbers (see [Number Formats](number_format.md))
* In the field tables, the leftmost field is the most-significant (i.e. at the highest address)
* In the word tables, `w0` is the lowest address of a record, and the table lists the words in address order. In the bounding volume and primitive word tables, the last column shows when the RTU reads each word

# Memory Map

| Address | Contents |
|----|----|
| 0-16 | Header, 17 words |
| 17 to 17 + 5 $\times$ `BV_NUM` - 1 | Bounding volumes, 5 words each, up to 16 |
| After the last bounding volume | Primitives: 7 words per sphere, 12 words per triangle |
| After the last primitive, up to 511 | Free |

The primitives are stored bounding volume by bounding volume: the primitives of each bounding volume are contiguous, and the bounding volumes' primitive lists are in bounding volume order.

# Header

| Field | CAM_Z | SPARE | BV_NUM | SPP_LOG2 | GROUND | SKY | U | R | F |
|----|----|----|----|----|----|----|----|----|----|
| Bit Width | 16 bits | 8 bits | 5 bits | 3 bits | 48 bits | 48 bits | 48 bits | 48 bits | 48 bits |

* 272 bits/17 words, at addresses 0-16
* The RTU reads all 17 words into its header registers once, when a RENDER message arrives, and never reads them again during the render
* `F` is the forward vector from the camera to the centre of the screen, with length 1. `R` points from the centre of the screen to its right edge and `U` from the centre to its top edge; both have length $\tan(\text{fov} / 2)$. The field of view must be 90° or less
* The host computes `F`, `R`, and `U` from the camera's yaw, pitch, and field of view, so the chip needs no sine or cosine to make camera rays
* `SKY` holds the horizon colour and the top colour. `GROUND` holds the two checker colours A and B of the ground plane
* `BV_NUM` is the number of bounding volumes, 0-16
* `SPP_LOG2` is $\log_2$ of the samples per pixel, 0-5 (1 to 32 samples); 6 and 7 are unused
* `CAM_Z` is the camera height (POS, 0 to 255.99). The camera is always at x = 0, y = 0: the host moves the scene so that it is
* Unlike the primitives, the header's vectors are stored x, y, z in address order

| Word | Contents | Format |
|:----:|----|:----:|
| `w0`, `w1`, `w2` | `F.x`, `F.y`, `F.z` | DIR |
| `w3`, `w4`, `w5` | `R.x`, `R.y`, `R.z` | DIR |
| `w6`, `w7`, `w8` | `U.x`, `U.y`, `U.z` | DIR |
| `w9` | horizon red [15:8], horizon green [7:0] | Colour |
| `w10` | horizon blue [15:8], top red [7:0] | Colour |
| `w11` | top green [15:8], top blue [7:0] | Colour |
| `w12` | A red [15:8], A green [7:0] | Colour |
| `w13` | A blue [15:8], B red [7:0] | Colour |
| `w14` | B green [15:8], B blue [7:0] | Colour |
| `w15` | `SPARE` [15:8], `BV_NUM` [7:3], `SPP_LOG2` [2:0] | Integer |
| `w16` | `CAM_Z` | POS |

# Spherical Bounding Volumes

| Field | X | Y | Z | R | BV_START | BV_COUNT |
|----|----|----|----|----|:----:|:----:|
| Bit Width | 16 bits | 16 bits | 16 bits | 16 bits | 9 bits | 7 bits |

* 80 bits/5 words per bounding volume
* Bounding volume $i$ starts at address 17 + 5$i$
* `X`, `Y`, `Z` are the centre and `R` is the radius (POS)
* `BV_START` is a base address in SRAM where the first object in a bounding volume is found
* `BV_COUNT` is the number of objects in a bounding volume
* The host builds the bounding volumes: each one is a sphere around a few nearby objects. If a ray cannot reach a bounding volume, the RTU skips all of its objects

| Word | Contents | Read |
|:----:|----|----|
| `w0` | `BV_START` [15:7], `BV_COUNT` [6:0] | Only if the ray can reach the bounding volume |
| `w1` | `R` | Every bounding volume test |
| `w2` | `Z` | Every bounding volume test |
| `w3` | `Y` | Every bounding volume test |
| `w4` | `X` | Every bounding volume test |

# Spherical Primitives

| Field | X | Y | Z | R | STRENGTH | MAT | RED | GREEN | BLUE | BV | TYPE |
|----|----|----|----|----|----|----|----|:----:|----|----|----|
| Bit Width | 16 bits | 16 bits | 16 bits | 16 bits | 14 bits | 2 bits | 8 bits | 8 bits | 8 bits | 7 bits | 1 bit |

* 112 bits/7 words per sphere
* `X`, `Y`, `Z` are the centre and `R` is the radius (POS)
* `STRENGTH` is the glow strength (Q4.10, 0 to 15.99, 1024 = 1.0), used only by `MAT_EMISSIVE`
* `MAT` specifies material type
* `RED`, `GREEN`, and `BLUE` represent 8-bit colour values
* `BV` is the index of the bounding volume the primitive belongs to. The host uses it to build the bounding volumes; the chip never reads it
* `TYPE` represents primitive type (`prim_type_t`: `PRIM_TRI` = 0, `PRIM_SPH` = 1). The RTU reads it first: it sets the size of the record (7 or 12 words) and so the address of the next primitive

| `mat_type_t` | Encoding | Material Type | Behaviour |
|----|:----:|----|----|
| `MAT_DIFFUSE` | 00 | Diffuse (matte) | Bounces in a random direction around the surface normal |
| `MAT_REFLECT` | 01 | Reflective (perfect mirror) | Reflects, with no random part |
| `MAT_DIELEC` | 10 | Dielectric (glass, index of refraction 1.5) | Reflects or refracts; spheres only |
| `MAT_EMISSIVE` | 11 | Emissive (glow) | Ends the path with the object colour $\times$ `STRENGTH` |

| Word | Contents | Read |
|:----:|----|----|
| `w0` | `BLUE` [15:8], `BV` [7:1], `TYPE` [0] | Every sphere test (`TYPE`), and for the closest hit |
| `w1` | `RED` [15:8], `GREEN` [7:0] | Closest hit only |
| `w2` | `STRENGTH` [15:2], `MAT` [1:0] | Closest hit only |
| `w3` | `R` | Every sphere test |
| `w4` | `Z` | Every sphere test |
| `w5` | `Y` | Every sphere test |
| `w6` | `X` | Every sphere test |

# Triangular Primitives

| Field | X | Y | Z | E1X  | E1Y | E1Z | E2X | E2Y | E2Z | STRENGTH | MAT | RED | GREEN | BLUE | BV | TYPE |
|----|----|----|----|----|----|----|----|----|----|----|----|----|:----:|----|----|----|
| Bit Width | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 14 bits | 2 bits | 8 bits | 8 bits | 8 bits | 7 bits | 1 bit |

* 192 bits/12 words per triangle
* `X`, `Y`, `Z` are the coordinates of corner $v_0$
* `E1X`, `E1Y`, `E1Z` are the elements of edge 1, $e_1 = v_1 - v_0$
* `E2X`, `E2Y`, `E2Z` are the elements of edge 2, $e_2 = v_2 - v_0$
* `STRENGTH`, `MAT`, `RED`, `GREEN`, `BLUE`, `BV`, and `TYPE` are the same as for a sphere. Triangles cannot be glass

| Word | Contents | Read |
|:----:|----|----|
| `w0` | `BLUE` [15:8], `BV` [7:1], `TYPE` [0] | Every triangle test (`TYPE`), and for the closest hit |
| `w1` | `RED` [15:8], `GREEN` [7:0] | Closest hit only |
| `w2` | `STRENGTH` [15:2], `MAT` [1:0] | Closest hit only |
| `w3`, `w4`, `w5` | `E2Z`, `E2Y`, `E2X` | Every triangle test, and for the closest hit's normal |
| `w6`, `w7`, `w8` | `E1Z`, `E1Y`, `E1X` | Every triangle test, and for the closest hit's normal |
| `w9`, `w10`, `w11` | `Z`, `Y`, `X` | Every triangle test |

# Ground Plane

The ground plane is fixed in the chip and is not stored in SRAM. It lies at z = 0 and is always on. It is a checkerboard of 4 $\times$ 4 squares in the header's checker colours A and B: colour B where bit 9 of the hit point's raw x XOR bit 9 of its raw y is 1 (bit 9 of a POS raw value is worth 4). Its surface normal is (0, 0, 1) and it is matte.

# Host Rules

The host builds the SRAM image and must keep the scene within the limits of the chip's number formats (see [Number Formats](number_format.md)):

* Move the scene so that the camera is at x = 0, y = 0
* Keep every position within $\pm$256
* Keep any two points the chip subtracts (a bounding volume or sphere centre and a ray origin, a triangle corner and a ray origin) less than 256 apart in each coordinate
* Keep every object at z $\ge$ 0. The RTU tests the ground only when no object was hit, which gives the right answer only if no object is below the ground
* Keep the field of view at 90° or less
