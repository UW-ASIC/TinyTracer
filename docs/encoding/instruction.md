# Instruction Encoding

## Macro-Operations

### Macro Opcodes

* `M_ADD = 5'b00000` (scalar addition)
* `M_SUB = 5'b00001` (scalar subtraction)
* `M_EQ = 5'b00010` (== operator)
* `M_NE = 5'b00011` (!= operator)
* `M_LT = 5'b00100` (< operator)
* `M_GE = 5'b00101`(>= operator)
* `M_MUL = 5'b00110` (scalar multiplication)
* `M_DIV = 5'b00111` (scalar division)
* `M_SQRT = 5'b01000` (scalar square root)
* `M_COS = 5'b01001` (cosine)
* `M_RECP = 5'b01010` (reciprocal)
* `M_RNG = 5'b01011` (random number generator)
* `M_VADD = 5'b01100` (vector addition)
* `M_VSUB = 5'b01101` (vector subtraction)
* `M_SCAL_VEC = 5'b01110` (scalar-vector multiplication)
* `M_DOT = 5'b01111` (vector dot product)
* `M_CROSS = 5'b10000` (vector cross product)
* `M_NORM = 5'b10001` (vector normalization)
* `M_SPHERE_NORM = 5'b10010` (vector normalization using sphere radius)

### Instructions

| Field | u3 | u2 | u1 | v3 | v2 | v1 | MACROOP |
|----|----|----|----|----|----|----|:----:|
| Bit Width | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 5 bits |

$$
\mathbf{\vec{u}}=\begin{pmatrix}u_3 \\ u_2 \\ u_1 \end{pmatrix}
\mathbf{\vec{v}}=\begin{pmatrix}v_3 \\ v_2 \\ v_1 \end{pmatrix}
$$

* `MACRO_W` = 101 bits
* For scalar operations, use $u_1$ and $v_1$ as operands
* For scalar-vector multiplication, use $u_1$ as scalar multiplier
* For normalization in sphere mode, use $u_1$ as sphere radius value

## Micro-Operations

### Micro Opcodes

* `U_ADD = 4'b0000` (scalar addition)
* `U_SUB = 4'b0001` (scalar subtraction)
* `U_EQ = 4'b0010` (== operator)
* `U_NE = 4'b0011` (!= operator)
* `U_LT = 4'b0100` (< operator)
* `U_GE = 4'b0101`(>= operator)
* `U_MUL = 4'b0110` (scalar multiplication)
* `U_DIV = 4'b0111` (scalar division)
* `U_SQRT = 4'b1000` (scalar square root)
* `U_COS = 4'b1001` (cosine)
* `U_RECP = 4'b1010` (reciprocal)
* `U_RNG = 4'b1011` (random number generator)

### Instructions

| Field | RD | RS1 | RS2 | MICROOP |
|----|----|----|----|:----:|
| Bit Width | 3 bits | 3 bits | 3 bits | 4 bits |

* `MICRO_W` = 13 bits
* Result is written in register specified in RD field 
* Operands are selected from registers RS1 and RS2 

## Functional Units

* Once a micro-op is received by `fu_control`, a functional unit is selected based on the `MICROOP` field
  * `ADD`, `SUB`, `EQ`, `NE`, `LT`, `GE` map to the ALU
  * `MUL` maps to the multiplier
  * `DIV`, `SQRT`, `COS`, `RECP` map to CORDIC
  * `RNG` maps to RNG
* Micro opcodes are remapped to functional unit opcodes as shown below

### Functional Unit Opcodes

#### ALU

* `ALU_ADD = 3'b000`
* `ALU_SUB = 3'b001`
* `ALU_EQ = 3'b010`
* `ALU_NE = 3'b011`
* `ALU_LT = 3'b100`
* `ALU_GE = 3'b101`

#### Multiplier

* N/A, multiplier has no opcode since it only multiplies

#### CORDIC

* `CORDIC_DIV = 3'b000`
* `CORDIC_SQRT = 3'b001`
* `CORDIC_COS = 3'b010`
* `CORDIC_RECP = 3'b011`

#### RNG

* N/A, RNG has no opcode since it only generates random numbers

# Macro to Micro Decomposition

* These decompositions are represented using the micro-op encoding listed above
* For each vector macro-op, the register file is populated based on the initial values described in each operation; the unspecified registers are left unchanged
  * The output mapping describes how the Decode Unit interprets the register file's contents before sending a macro-op result back to the RTU
* For scalar macro-ops, write scalar operands to R0 and R1 and set R0 to the destination register as well

#### Vector Add

Operation: $\vec{w} = \vec{u}+\vec{v}$

* __Initial Register File State__:
    * R0 $\leftarrow$ $u_1$
    * R1 $\leftarrow$ $u_2$
    * R2 $\leftarrow$ $u_3$
    * R3 $\leftarrow$ $v_1$
    * R4 $\leftarrow$ $v_2$
    * R5 $\leftarrow$ $v_3$
* __Instructions:__
    * ADD R0 $\leftarrow$ R0, R3 ($u_1$+$v_1$)
    * ADD R1 $\leftarrow$ R1, R4 ($u_2$+$v_2$)
    * ADD R2 $\leftarrow$ R2, R5 ($u_3$+$v_3$)
* __Output Mapping:__
    * $w_1$ = R0
    * $w_2$ = R1
    * $w_3$ = R2

#### Vector Subtract

Operation: $\vec{w} = \vec{u}-\vec{v}$

* __Initial Register File State__:
    * R0 $\leftarrow$ $u_1$
    * R1 $\leftarrow$ $u_2$
    * R2 $\leftarrow$ $u_3$
    * R3 $\leftarrow$ $v_1$
    * R4 $\leftarrow$ $v_2$
    * R5 $\leftarrow$ $v_3$
* __Instructions__:
    * SUB R0 $\leftarrow$ R0, R3 ($u_1$-$v_1$)
    * SUB R1 $\leftarrow$ R1, R4 ($u_2$-$v_2$)
    * SUB R2 $\leftarrow$ R2, R5 ($u_3$-$v_3$)
* __Output Mapping__
    * $w_1$ = R0
    * $w_2$ = R1
    * $w_3$ = R2

#### Scalar-Vector Multiplication

Operation: $\vec{w} = u_1*\vec{v}$

* __Initial Register File State__:
    * R0 $\leftarrow$ $u_1$
    * R1 $\leftarrow$ $v_1$
    * R2 $\leftarrow$ $v_2$
    * R3 $\leftarrow$ $v_3$
* __Instructions__:
    * MUL R1 $\leftarrow$ R0, R1 ($u_1$\*$v_1$)
    * MUL R2 $\leftarrow$ R0, R2 ($u_1$\*$v_2$)
    * MUL R3 $\leftarrow$ R0, R3 ($u_1$\*$v_3$)
* __Output Mapping__:
    * $w_1$ = R1
    * $w_2$ = R2
    * $w_3$ = R3

#### Vector Dot Product

Operation: $s = \vec{u} \cdot \vec{v}$

* __Initial Register File State__:
    * R0 $\leftarrow$ $u_1$
    * R1 $\leftarrow$ $u_2$
    * R2 $\leftarrow$ $u_3$
    * R3 $\leftarrow$ $v_1$
    * R4 $\leftarrow$ $v_2$
    * R5 $\leftarrow$ $v_3$
* __Instructions__:
    * MUL R0 $\leftarrow$ R0, R3 ($u_1$\*$v_1$)
    * MUL R1 $\leftarrow$ R1, R4 ($u_2$\*$v_2$)
    * MUL R2 $\leftarrow$ R2, R5 ($u_3$\*$v_3$)
    * ADD R0 $\leftarrow$ R0, R1 ($u_1$\*$v_1$ + $u_2$\*$v_2$)
    * ADD R0 $\leftarrow$ R0, R2 ($u_1$\*$v_1$ + $u_2$\*$v_2$ + $u_3$\*$v_3$)
* __Output Mapping__:
    * $s$ = R0

#### Vector Cross Product

Operation: $\vec{w} = \vec{u} \times \vec{v}$

* __Initial Register File State__:
    * R0 $\leftarrow$ $u_1$
    * R1 $\leftarrow$ $u_2$
    * R2 $\leftarrow$ $u_3$
    * R3 $\leftarrow$ $v_1$
    * R4 $\leftarrow$ $v_2$
    * R5 $\leftarrow$ $v_3$
* __Instructions__:
    * MUL R6 $\leftarrow$ R0, R5 ($u_1$\*$v_3$)
    * MUL R0 $\leftarrow$ R0, R4 ($u_1$\*$v_2$)
    * MUL R5 $\leftarrow$ R1, R5 ($u_2$\*$v_3$)
    * MUL R1 $\leftarrow$ R1, R3 ($u_2$\*$v_1$)
    * SUB R0 $\leftarrow$ R0, R1 ($u_1$\*$v_2$ - $u_2$\*$v_1$)
    * MUL R1 $\leftarrow$ R2, R4 ($u_3$\*$v_2$)
    * SUB R1 $\leftarrow$ R5, R1 ($u_2$\*$v_3$ - $u_3$\*$v_2$)
    * MUL R2 $\leftarrow$ R2, R3 ($u_3$\*$v_1$)
    * SUB R2 $\leftarrow$ R2, R6 ($u_3$\*$v_1$ - $u_1$\*$v_3$)
* __Output Mapping__:
    * $w_1$ = R1
    * $w_2$ = R2
    * $w_3$ = R0

#### Vector Normalization

Operation: $\vec{w} = \frac{\vec{u}}{|\vec{u}|}$

**Default Mode:**

* __Initial Register File State__:
    * R0 $\leftarrow$ $u_1$
    * R1 $\leftarrow$ $u_2$
    * R2 $\leftarrow$ $u_3$
* __Instructions__:
    * MUL R3 $\leftarrow$ R0, R0 ($u_1$\*$u_1$)
    * MUL R4 $\leftarrow$ R1, R1 ($u_2$\*$u_2$)
    * MUL R5 $\leftarrow$ R2, R2 ($u_3$\*$u_3$)
    * ADD R3 $\leftarrow$ R3, R4 ($u_1$\*$u_1$ + $u_2$\*$u_2$)
    * ADD R3 $\leftarrow$ R3, R5 ($u_1$\*$u_1$ + $u_2$\*$u_2$ + $u_3$\*$u_3$)
    * SQRT R3 $\leftarrow$ R3 ($\sqrt{u_1*u_1 + u_2*u_2 + u_3*u_3}$)
    * RECP R3 $\leftarrow$ R3 ($1/\sqrt{u_1*u_1 + u_2*u_2 + u_3*u_3}$)
    * MUL R0 $\leftarrow$ R3, R0 ($1/\sqrt{u_1*u_1 + u_2*u_2 + u_3*u_3}$ * $u_1$)
    * MUL R1 $\leftarrow$ R3, R1 ($1/\sqrt{u_1*u_1 + u_2*u_2 + u_3*u_3}$ * $u_2$)
    * MUL R2 $\leftarrow$ R3, R2 ($1/\sqrt{u_1*u_1 + u_2*u_2 + u_3*u_3}$ * $u_3$)
* __Output Mapping__:
    * $w_1$ = R0
    * $w_2$ = R1
    * $w_3$ = R2

**Sphere Mode:**

* __Initial Register File State__:
    * R0 $\leftarrow$ $v_1$
    * R1 $\leftarrow$ $v_2$
    * R2 $\leftarrow$ $v_3$
    * R3 $\leftarrow$ $u_1$ (sphere radius)
* __Instructions__:
    * DIV R0 $\leftarrow$ R0, R3 ($v_1$ / $r$)
    * DIV R1 $\leftarrow$ R1, R3 ($v_2$ / $r$)
    * DIV R2 $\leftarrow$ R2, R3 ($v_3$ / $r$)
* __Output Mapping__:
    * $w_1$ = R0
    * $w_2$ = R1
    * $w_3$ = R2