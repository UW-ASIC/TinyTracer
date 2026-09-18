# Scene Encoding

* Each object has its shape and material encoded in a custom format
* The following assumes we use 16 bit precision and 16 bit word length
* For the following encodings, the leftmost word is the most-significant (i.e. the last word to be fetched from SRAM)

# Spherical Bounding Volumes

| Field | X | Y | Z | R | BV_START | BV_COUNT |
|----|----|----|----|----|:----:|:----:|
| Bit Width | 16 bits | 16 bits | 16 bits | 16 bits | 9 bits | 7 bits |

* 80 bits/10 bytes per bounding volume
* `BV_START` is a base address in SRAM where the first object in a bounding volume is found
* `BV_COUNT` is the number of objects in a bounding volume

# Spherical Primitives

| Field | X | Y | Z | R | ALB | MAT | RED | GREEN | BLUE | BV | TYPE |
|----|----|----|----|----|----|----|----|:----:|----|----|----|
| Bit Width | 16 bits | 16 bits | 16 bits | 16 bits | 14 bits | 2 bits | 8 bits | 8 bits | 8 bits | 7 bits | 1 bit |

* 112 bits/14 bytes per sphere
* `ALB` represents albedo, or how much a material absorbs/reflects light
* `MAT` specifies material type
* `RED`, `GREEN`, and `BLUE` represent 8-bit colour values
* `BV` represents the bounding volume shape the primitive resides in
* `TYPE` represents primitive type (0 for triangle, 1 for sphere)

| `mat_type_t` | Encoding | Material Type |
|----|:----:|----|
| `MAT_DIFFUSE` | 00 |Diffuse |
| `MAT_REFLECT` | 01 | Reflective |
| `MAT_DIELEC` | 10 | Dielectric (Glass) |
| `MAT_EMISSIVE` | 11 | Emissive |

# Triangular Primitives

| Field | X | Y | Z | UX  | UY | UZ | VX | VY | VZ | ALB | MAT | RED | GREEN | BLUE | BV | TYPE |
|----|----|----|----|----|----|----|----|----|----|----|----|----|:----:|----|----|----|
| Bit Width | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 14 bits | 2 bits | 8 bits | 8 bits | 8 bits | 7 bits | 1 bit |

* 192 bits/24 bytes per triangle
* `X`, `Y`, `Z` are the origin coordinates
* `UX`, `UY`, `UZ` are the elements of the u plane vector
* `VX`, `VY`, `VZ` are the elements of the v plane vector

