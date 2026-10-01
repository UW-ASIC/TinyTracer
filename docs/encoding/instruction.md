---
description: "Encoding of the macro-ops the RTU issues and the micro-ops the Decode Unit sends to the functional units."
---

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
* `M_COS = 5'b01001` (scaled cosine, $u_1\cos(v_1)$)
* `M_MAG = 5'b01011` (2D vector magnitude)
* `M_VADD = 5'b01100` (vector addition)
* `M_VSUB = 5'b01101` (vector subtraction)
* `M_SCAL_VEC = 5'b01110` (scalar-vector multiplication)
* `M_DOT = 5'b01111` (vector dot product)
* `M_CROSS = 5'b10000` (vector cross product)
* `M_NORM = 5'b10001` (vector normalization)
* `M_SPHERE_NORM = 5'b10010` (vector normalization using sphere radius)
* `M_VMUL = 5'b10011` (vector element-wise multiplication)

Macro-ops `M_ADD` to `M_MAG` are scalar macro-ops and `M_VADD` to `M_VMUL` are vector macro-ops. Macro opcode `5'b01010` is unused. The RTU does not use `M_EQ`, `M_NE`, or `M_GE` (`M_GE` is the inverse of `M_LT`), and uses `M_MAG` only as a micro-op inside `M_NORM`.

### Instructions

| Field | FMT | u3 | u2 | u1 | v3 | v2 | v1 | MACROOP |
|----|----|----|----|----|----|----|----|:----:|
| Bit Width | 1 bit | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 16 bits | 5 bits |
| Bits | [101] | [100:85] | [84:69] | [68:53] | [52:37] | [36:21] | [20:5] | [4:0] |

$$
\mathbf{\vec{u}}=\begin{pmatrix}u_3 \\ u_2 \\ u_1 \end{pmatrix}
\mathbf{\vec{v}}=\begin{pmatrix}v_3 \\ v_2 \\ v_1 \end{pmatrix}
$$

* `MACRO_W` = 102 bits
* `op.u` and `op.v` correspond to operands $\mathbf{\vec{u}}$ and $\mathbf{\vec{v}}$ 
* `op.u.x`, `op.u.y`, `op.u.z` correspond to $u_1$, $u_2$, and $u_3$ respectively for $\mathbf{\vec{u}}$ 
* For scalar operations, use $u_1$ and $v_1$ as operands
* For scalar-vector multiplication, use $u_1$ as scalar multiplier
* For normalization in sphere mode, use $u_1$ as sphere radius value
* `FMT` (`fmt_t`: `FMT_POS` = 0, `FMT_DIR` = 1) selects the number format of the result (see [Number Formats](number_format.md)):
    * `MUL` micro-ops shift the 32-bit product right by 7 bits when `FMT` = 0 (POS $\times$ POS $\rightarrow$ POS) and by 14 bits when `FMT` = 1 (a product with a DIR operand)
    * `SQRT` micro-ops take and return POS when `FMT` = 0 and DIR when `FMT` = 1
    * All other micro-ops ignore `FMT`
* The colour multiplies of the Shader Core need shifts of 8 and 10, which one `FMT` bit cannot select. This is still open: either `FMT` grows to a 2-bit select of $\{7, 8, 10, 14\}$ (`MACRO_W` = 103 bits), or the Shader Core gets its own colour multiplier

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
* `U_COS = 4'b1001` (scaled cosine)
* `U_MAG = 4'b1011` (vector magnitude)

### Instructions

| Field | RD | RS1 | RS2 | MICROOP |
|----|----|----|----|:----:|
| Bit Width | 3 bits | 3 bits | 3 bits | 4 bits |

* `MICRO_W` = 13 bits
* Result is written in register specified in RD field 
* Operands are selected from registers RS1 and RS2 
* The macro-op's `FMT` bit is sent to FU Control alongside every micro-op; it is not part of the micro-op word

### Micro-Op Semantics

| Micro-op | Computes | Functional Unit | Latency (cycles) |
|----|----|----|:----:|
| `U_ADD`, `U_SUB` | RD $\leftarrow$ RS1 $\pm$ RS2, clamped | ALU | 1 |
| `U_EQ`, `U_NE`, `U_LT`, `U_GE` | RD $\leftarrow$ 1 if the compare is true, else 0 | ALU | 1 |
| `U_MUL` | RD $\leftarrow$ RS1 $\times$ RS2, shifted right by 7 or 14 bits (`FMT`), rounded, clamped | Multiplier | 1 |
| `U_DIV` | RD $\leftarrow$ (RS1 $\ll$ 14) $\div$ RS2, clamped | CORDIC | 17 |
| `U_SQRT` | RD $\leftarrow \sqrt{\text{RS1}}$, POS or DIR (`FMT`); RS2 not used | CORDIC | 23 |
| `U_COS` | RD $\leftarrow$ RS1 $\times \cos(\text{RS2})$, RS2 in radians (DIR); the result has the format of RS1 | CORDIC | 18 |
| `U_MAG` | RD $\leftarrow \sqrt{\text{RS1}^2 + \text{RS2}^2}$ | CORDIC | 19 |

* A micro-op issued in cycle $k$ on a unit with latency $L$ completes in cycle $k + L$, and its result is written at the end of that cycle
* The ALU and multiplier latencies of 1 cycle are assumptions. The CORDIC latencies are the worst cases of the [CORDIC](../modules/exu/functional_units/cordic.md) timing table with 16 iterations

## Functional Units

* Once a micro-op is received by `fu_control`, a functional unit is selected based on the `MICROOP` field
  * `ADD`, `SUB`, `EQ`, `NE`, `LT`, `GE` map to the ALU
  * `MUL` maps to the multiplier
  * `DIV`, `SQRT`, `COS`, `MAG` map to CORDIC. RS1 is the CORDIC operand $A$ and RS2 is $B$ (see [CORDIC](../modules/exu/functional_units/cordic.md))
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

* `CORDIC_DIV = 2'b00` ($A / B$)
* `CORDIC_SQRT = 2'b01` ($\sqrt{A}$)
* `CORDIC_COS = 2'b10` ($A\cos B$)
* `CORDIC_MAG = 2'b11` ($\sqrt{A^2 + B^2}$)

# Macro to Micro Decomposition

* These decompositions are represented using the micro-op encoding listed above
* Every macro-op loads the register file with the same layout in a single cycle: R0, R1, R2 $\leftarrow$ $u_1$, $u_2$, $u_3$ and R3, R4, R5 $\leftarrow$ $v_1$, $v_2$, $v_3$; R6 and R7 are left unchanged
  * The initial register file state listed for each operation shows only the registers that operation uses
* Every macro-op leaves its result in R0-R2 ($w_1$, $w_2$, $w_3$), which the register file sends back to the RTU directly; scalar results are in R0
  * The output mapping in each operation shows where each result element is
* Micro-ops read their source registers when they are issued, so a micro-op may overwrite a register that an earlier, still in-flight micro-op reads (see Scalar-Vector Multiplication)
* Scalar macro-ops have no ROM rows. The single micro-op is OP R0 $\leftarrow$ $u_1$, $v_1$ (unary operations only use $u_1$), where OP is the low 4 bits of `MACROOP`. It is issued in the cycle the macro-op is accepted, with its operands taken straight from the request rather than from the register file, and its result is written to R0

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
    * R3 $\leftarrow$ $v_1$
    * R4 $\leftarrow$ $v_2$
    * R5 $\leftarrow$ $v_3$
* __Instructions__:
    * MUL R1 $\leftarrow$ R0, R4 ($u_1$\*$v_2$)
    * MUL R2 $\leftarrow$ R0, R5 ($u_1$\*$v_3$)
    * MUL R0 $\leftarrow$ R0, R3 ($u_1$\*$v_1$), issued last since it overwrites $u_1$
* __Output Mapping__:
    * $w_1$ = R0
    * $w_2$ = R1
    * $w_3$ = R2

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
    * MUL R6 $\leftarrow$ R2, R4 ($u_3$\*$v_2$)
    * MUL R2 $\leftarrow$ R2, R3 ($u_3$\*$v_1$)
    * MUL R4 $\leftarrow$ R0, R4 ($u_1$\*$v_2$)
    * MUL R3 $\leftarrow$ R1, R3 ($u_2$\*$v_1$)
    * MUL R1 $\leftarrow$ R1, R5 ($u_2$\*$v_3$)
    * MUL R5 $\leftarrow$ R0, R5 ($u_1$\*$v_3$)
    * SUB R0 $\leftarrow$ R1, R6 ($u_2$\*$v_3$ - $u_3$\*$v_2$)
    * SUB R1 $\leftarrow$ R2, R5 ($u_3$\*$v_1$ - $u_1$\*$v_3$)
    * SUB R2 $\leftarrow$ R4, R3 ($u_1$\*$v_2$ - $u_2$\*$v_1$)
* __Output Mapping__:
    * $w_1$ = R0
    * $w_2$ = R1
    * $w_3$ = R2

#### Vector Normalization

Operation: $\vec{w} = \frac{\vec{u}}{|\vec{u}|}$

**Default Mode:**

* __Initial Register File State__:
    * R0 $\leftarrow$ $u_1$
    * R1 $\leftarrow$ $u_2$
    * R2 $\leftarrow$ $u_3$
    * R3 $\leftarrow$ $v_1$ = 1.0 (DIR), a constant the RTU puts in the request
* __Instructions__:
    * MAG R4 $\leftarrow$ R0, R1 ($\sqrt{{u_1}^2+{u_2}^2}$)
    * MAG R4 $\leftarrow$ R4, R2 ($\sqrt{{u_1}^2+{u_2}^2+{u_3}^2}$)
    * DIV R4 $\leftarrow$ R3, R4 ($1/\sqrt{{u_1}^2+{u_2}^2+{u_3}^2}$)
    * MUL R0 $\leftarrow$ R4, R0 ($1/\sqrt{{u_1}^2+{u_2}^2+{u_3}^2}$ * $u_1$)
    * MUL R1 $\leftarrow$ R4, R1 ($1/\sqrt{{u_1}^2+{u_2}^2+{u_3}^2}$ * $u_2$)
    * MUL R2 $\leftarrow$ R4, R2 ($1/\sqrt{{u_1}^2+{u_2}^2+{u_3}^2}$ * $u_3$)
* __Output Mapping__:
    * $w_1$ = R0
    * $w_2$ = R1
    * $w_3$ = R2

**Sphere Mode:**

* __Initial Register File State__:
    * R0 $\leftarrow$ $u_1$ (sphere radius)
    * R3 $\leftarrow$ $v_1$
    * R4 $\leftarrow$ $v_2$
    * R5 $\leftarrow$ $v_3$
* __Instructions__:
    * DIV R1 $\leftarrow$ R4, R0 ($v_2$ / $r$)
    * DIV R2 $\leftarrow$ R5, R0 ($v_3$ / $r$)
    * DIV R0 $\leftarrow$ R3, R0 ($v_1$ / $r$), issued last since it overwrites $r$
* __Output Mapping__:
    * $w_1$ = R0
    * $w_2$ = R1
    * $w_3$ = R2

#### Vector Element-Wise Multiplication

Operation: $\vec{w} = \vec{u} \odot \vec{v}$, i.e. $w_i = u_i v_i$ (used for colours)

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
* __Output Mapping__:
    * $w_1$ = R0
    * $w_2$ = R1
    * $w_3$ = R2
