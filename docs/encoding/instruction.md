# Instruction Encoding

# Macro-Operations

## Macro Opcodes

* `ADD = 5'b00000` (scalar addition)
* `SUB = 5'b00001` (scalar subtraction)
* `EQ = 5'b00010` (== operator)
* `NE = 5'b00011` (!= operator)
* `LT = 5'b00100` (< operator)
* `GE = 5'b00101`(>= operator)
* `MUL = 5'b00110` (scalar multiplication)
* `DIV = 5'b00111` (scalar division)
* `SQRT = 5'b01000` (scalar square root)
* `COS = 5'b01001` (cosine)
* `RECP = 5'b01010` (reciprocal)
* `RNG = 5'b01011` (random number generator)
* `VADD = 5'b01100` (vector addition)
* `VSUB = 5'b01101` (vector subtraction)
* `SCAL_VEC = 5'b01110` (scalar-vector multiplication)
* `DOT = 5'b01111` (vector dot product)
* `CROSS = 5'b10000` (vector cross product)
* `NORM = 5'b10001` (vector normalization)
* `SPHERE_NORM = 5'b10010` (vector normalization using sphere radius)

## Instructions

* 6 scalar operands max (for vector ops) - 6\*16 bits = 96 bits
* `MACRO_W` = 101 bits

| Field | u3 | u2 | u1 | v3 | v2 | v1 | MACROOP |
|----|----|----|----|----|----|----|----|
| Bit Width | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 5 bits |

$$
\mathbf{\vec{u}}=\begin{pmatrix}u_3 \\ u_2 \\ u_1 \end{pmatrix}
\mathbf{\vec{v}}=\begin{pmatrix}v_3 \\ v_2 \\ v_1 \end{pmatrix}
$$

* For scalar operations, use u1 and v1 as operands
* For scalar-vector multiplication, use u1 as scalar multiplier
* For normalization in sphere mode, use u1 as sphere radius value

# Micro-Operations

## Micro Opcodes

* `ADD = 4'b0000` (scalar addition)
* `SUB = 4'b0001` (scalar subtraction)
* `EQ = 4'b0010` (== operator)
* `NE = 4'b0011` (!= operator)
* `LT = 4'b0100` (< operator)
* `GE = 4'b0101`(>= operator)
* `MUL = 4'b0110` (scalar multiplication)
* `DIV = 4'b0111` (scalar division)
* `SQRT = 4'b1000` (scalar square root)
* `COS = 4'b1001` (cosine)
* `RECP = 4'b1010` (reciprocal)
* `RNG = 4'b1011` (random number generator)

## Instructions

* Result is written in register specified in RD field - 3 bits
* Operands are selected from registers RS1 and RS2 - 2 \* 3 bits
* 12 micro-ops for scalar/vector operations - 4 bits
* `MICRO_W` = 13 bits

| Field | RD | RS1 | RS2 | MICROOP |
|----|----|----|----|----|
| Bit Width | 3 bits | 3 bits | 3 bits | 4 bits |

# Functional Units

* Once a micro-op is received, a functional unit is chosen based on the MICROOP field
  * ADD, SUB, EQ, NE, LT, GE map to ALU
  * MUL maps to multiplier
  * DIV, SQRT, COS, RECP map to CORDIC
  * RNG maps to RNG
* Micro opcodes are remapped to functional opcodes

## Functional Opcodes

### ALU

* `ADD = 3'b000`
* `SUB = 3'b001`
* `EQ = 3'b010`
* `NE = 3'b011`
* `LT = 3'b100`
* `GE = 3'b101`

### Multiplier

* N/A, multiplier has no opcode since it only multiplies

### CORDIC

* `DIV = 3'b000`
* `SQRT = 3'b001`
* `COS = 3'b010`
* `RECP = 3'b011`

### RNG

* N/A, RNG has no opcode since it only generates random numbers

# Macro to Micro Translations

* These translations are represented using the micro-op encoding listed above
* "-" represents don't care bits
* For each vector macro-op, the register file is populated based on the initial values described in each operation; the unspecified registers are left unchanged
  * The mapping describes how the decode logic interprets the register file's contents before sending a result back to the RTU
* For scalar macro-ops, write scalar operands to R0 and R1 and set R0 to the destination register as well

### Vector Add

Operation: $\vec{w} = \vec{u}+\vec{v}$

* __Initial Register File State__:
  * R0 <- u1
  * R1 <- u2
  * R2 <- u3
  * R3 <- v1
  * R4 <- v2
  * R5 <- v3
* __Instructions:__
  * ADD R0 <- R0, R3 (u1+v1)
  * ADD R1 <- R1, R4 (u2+v2)
  * ADD R2 <- R2, R5 (u3+v3)
* __Mapping:__
  * w1 = R0
  * w2 = R1
  * w3 = R2

### Vector Subtract

Operation: $\vec{w} = \vec{u}-\vec{v}$

* __Initial Register File State__:
  * R0 <- u1
  * R1 <- u2
  * R2 <- u3
  * R3 <- v1
  * R4 <- v2
  * R5 <- v3
* __Instructions__:
  * SUB R0 <- R0, R3 (u1-v1)
  * SUB R1 <- R1, R4 (u2-v2)
  * SUB R2 <- R2, R5 (u3-v3)
* __Mapping__
  * w1 = R0
  * w2 = R1
  * w3 = R2

### Scalar-Vector Multiplication

Operation: $\vec{w} = u_1*\vec{v}$

* __Initial Register File State__:
  * R0 <- u1
  * R1 <- v1
  * R2 <- v2
  * R3 <- v3
* __Instructions__:
  * MUL R1 <- R0, R1 (u1\*v1)
  * MUL R2 <- R0, R2 (u1\*v2)
  * MUL R3 <- R0, R3 (u1\*v3)
* __Mapping__:
  * w1 = R1
  * w2 = R2
  * w3 = R3

### Vector Dot Product

Operation: $s = \vec{u} \cdot \vec{v}$

* __Initial Register File State__:
  * R0 <- u1
  * R1 <- u2
  * R2 <- u3
  * R3 <- v1
  * R4 <- v2
  * R5 <- v3
* __Instructions__:
  * MUL R0 <- R0, R3 (u1\*v1)
  * MUL R1 <- R1, R4 (u2\*v2)
  * MUL R2 <- R2, R5 (u3\*v3)
  * ADD R0 <- R0, R1 (u1\*v1 + u2\*v2)
  * ADD R0 <- R0, R2 (u1\*v1 + u2\*v2 + u3\*v3)
* __Mapping__:
  * s = R0

### Vector Cross Product

Operation: $\vec{w} = \vec{u} \times \vec{v}$

* __Initial Register File State__:
  * R0 <- u1
  * R1 <- u2
  * R2 <- u3
  * R3 <- v1
  * R4 <- v2
  * R5 <- v3
* __Instructions__:
  * MUL R6 <- R0, R5 (u1\*v3)
  * MUL R0 <- R0, R4 (u1\*v2)
  * MUL R5 <- R1, R5 (u2\*v3)
  * MUL R1 <- R1, R3 (u2\*v1)
  * SUB R0 <- R0, R1 (u1\*v2 - u2\*v1)
  * MUL R1 <- R2, R4 (u3\*v2)
  * SUB R1 <- R5, R1 (u2\*v3 - u3\*v2)
  * MUL R2 <- R2, R3 (u3\*v1)
  * SUB R2 <- R2, R6 (u3\*v1 - u1\*v3)
* __Mapping__:
  * w1 = R1
  * w2 = R2
  * w3 = R0

### Vector Normalization

Operation: $\vec{w} = \frac{\vec{u}}{|\vec{u}|}$

**Default Mode:**

* __Initial Register File State__:
  * R0 <- u1
  * R1 <- u2
  * R2 <- u3
* __Instructions__:
  * MUL R3 <- R0, R0 (u1\*u1)
  * MUL R4 <- R1, R1 (u2\*u2)
  * MUL R5 <- R2, R2 (u3\*u3)
  * ADD R3 <- R3, R4 (u1\*u1 + u2\*u2)
  * ADD R3 <- R3, R5 (u1\*u1 + u2\*u2 + u3\*u3)
  * SQRT R3 <- R3 (sqrt(u1\*u1 + u2\*u2 + u3\*u3))
  * RECP R3 <- R3 (1/sqrt(u1\*u1 + u2\*u2 + u3\*u3))
  * MUL R0 <- R3, R0 (1/sqrt(u1\*u1 + u2\*u2 + u3\*u3) \* u1)
  * MUL R1 <- R3, R1 (1/sqrt(u1\*u1 + u2\*u2 + u3\*u3) \* u2)
  * MUL R2 <- R3, R2 (1/sqrt(u1\*u1 + u2\*u2 + u3\*u3) \* u3)
* __Mapping__:
  * w1 = R0
  * w2 = R1
  * w3 = R2

**Sphere Mode:**

* __Initial Register File State__:
  * R0 <- v1
  * R1 <- v2
  * R2 <- v3
  * R3 <- u1 (sphere radius)
* __Instructions__:
  * DIV R0 <- R0, R3 (v1 / r)
  * DIV R1 <- R1, R3 (v2 / r)
  * DIV R2 <- R2, R3 (v3 / r)
* __Mapping__:
  * w1 = R0
  * w2 = R1
  * w3 = R2