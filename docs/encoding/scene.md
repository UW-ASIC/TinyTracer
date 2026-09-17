# Scene Encoding

* Each object has its shape and material encoded in a custom format
* The following assumes we use 16 bit precision and 16 bit word length
* For the following encodings, the leftmost word is the most-significant (i.e. the last word to be fetched from SRAM)

# Spherical Bounding Volume Encoding

| Field | X | Y | Z | R | BV_START | BV_COUNT |
|----|----|----|----|----|----|----|
| Bit Width | 16 bits | 16 bits | 16 bits | 16 bits | 9 bits | 7 bits |

* 80 bits => 5 words or 10 bytes per bounding volume
* BV_START is the start address in SRAM where the first object in a bounding volume is found
* BV_COUNT is the number of objects in a bounding volume

# Triangular Primitive Encoding

| Field | X | Y | Z | UX  | UY | UZ | VX | VY | VZ | ALB | MAT | RED | GREEN | BLUE | BV | TYPE |
|----|----|----|----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| Bit Width | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 14 bits | 2 bits | 4 bits | 4 bits | 4 bits | 3 bits | 1 bit |

* 176 bits => 11 words or 22 bytes per triangle
* X, Y, Z are the origin coordinates
* UX, UY, UZ are the elements of the u plane vector
* VX, VY, VZ are the elements of the v plane vector
* ALB represents albedo, or how much a material absorbs/reflects light
* MAT specifies material type
* RED, GREEN, and BLUE represent 4-bit color values
* BV represents the bounding volume shape the primitive resides in
* TYPE represents primitive type (0 for triangle, 1 for sphere)

| MAT | Material Type |
|----|----|
| 00 | Diffuse |
| 01 | Reflective |
| 10 | Dielectric (Glass) |
| 11 | Emissive |

# Spherical Primitives

| Field | X | Y | Z | R | ALB | MAT | RED | GREEN | BLUE | BV | TYPE |
|----|----|----|----|----|----|----|----|----|----|----|----|
| Bit Width | 16 bits | 16 bits | 16 bits | 16 bits | 14 bits | 2 bits | 4 bits | 4 bits | 4 bits | 3 bits | 1 bit |

* 96 bits => 6 words or 12 bytes per sphere

# Summary

* 10 bytes per bounding volume, 22 bytes per triangle, 12 bytes per sphere
  * Can fit approximately 4 bounding volumes and 44 triangles or 88 spheres in SRAM
* Each primitive message encodes shape and material data
