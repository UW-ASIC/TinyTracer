# `cordic` — CORDIC Unit

## Overview

This module is a fixed-point CORDIC engine enabling support for division, cosine, vector magnitude, and square root. Its LUT is held in a ROM local to the module, so like the other FUs it only communicates with FU Control.

## Parameters

| Name          |   Default    | Description                           |
|---------------|:------------:|---------------------------------------|
| `WLEN`  |     16      | Word length              |
| `ITER`  |     `WLEN`      | Number of CORDIC iterations             |
| `Q_INT`       |     8      | Integer bits in fixed point format    |
| `Q_FRAC`      |     8      | Fractional bits in fixed point format |

## Ports

### Inputs

| Name          |   Width    | Description                           |
|---------------|:------------:|---------------------------------------|
| `clk`  |     1      | Clock signal |
| `rst_n`  |     1      | Active-low reset |
| `start` |     1       | Rising-edge triggered start input |
| `x_in`  |     N       | $x_0$ operator input |
| `y_in`  |     N       | $y_0$ operator input |
| `z_in`  |     N       | $z_0$ operator input |
| `opcode`|     2       | Operation to be performed (input) |
| `x_out` |     N       | $x_N$ value output |
| `y_out` |     N       | $y_N$ value output |
| `z_out` |     N       | $z_N$ value output |
| `busy` |     1       | Output for when engine is busy |


### Interfaces

| Type          | Description                           |
|---------------|---------------------------------------|
| `fu_if`  | Micro-op request and response channel from FU Control |

## Architecture Overview

The CORDIC engine is designed as a state machine with the following states:

- **IDLE**
    - Outputs are held stable, `busy` is held LOW. This state is for when the engine has completed the latest calculation, and is waiting for the next operation.
- **INIT**
    - Transitioned to after **IDLE** when `start` goes HIGH. Initializes the operation register and operand registers with the supplied values.
- **NORMALIZE**
    - Transitioned to in the next cycle after **INIT**. The input values are checked for whether or not they fit the CORDIC bounds (these bounds vary operation by operation), and normalized combinationally if required.
- **LOOP**
    - Transitioned to in 2 cycles after **NORMALIZE**. The main CORDIC loop is performed for the operation.
- **REVERT**
    - Transitioned to after N cycles (or N + R for square root) of **LOOP**. The CORDIC loop has concluded, the values now need to be un-normalized (meaning: radix-point realigned) if normalization had occurred.
- **POSTSCALE**
    - Transitioned to immediately after **REVERT**. Some CORDIC operations inadvertently apply a gain to the output. Multiply by the inverse of this gain to get the correct output. Since we are multiplying by a constant, we can avoid a multiplier and do it with just shifts and adds.

## LUTs

CORDIC engines require LUTs for retrieving important values during iterations. We'll need two LUTs:

1. An arctan LUT:

| Entry | Shift Index i | atan(2^-i) |
| --- | --- | --- |
| 0 | 0 | 0.785398163397 |
| 1 | 1 | 0.463647609000 |
| 2 | 2 | 0.244978663126 |
| 3 | 3 | 0.124354994546 |
| 4 | 4 | 0.062418809995 |
| 5 | 5 | 0.031239833430 |
| 6 | 6 | 0.015623728620 |
| 7 | 7 | 0.007812341060 |
| 8 | 8 | 0.003906230131 |
| 9 | 9 | 0.001953122516 |
| 10 | 10 | 0.000976562189 |
| 11 | 11 | 0.000488281211 |
| 12 | 12 | 0.000244140620 |
| 13 | 13 | 0.000122070312 |
| 14 | 14 | 0.000061035156 |
| 15 | 15 | 0.000030517578 |

2. An atanh LUT:

| Entry | Shift Index i | atanh(2^-i) |
| --- | --- | --- |
| 0 | 1 | 0.549306144334 |
| 1 | 2 | 0.255412811882 |
| 2 | 3 | 0.125657214140 |
| 3 | 4 | 0.062581571477 |
| 4 | 5 | 0.031260178492 |
| 5 | 6 | 0.015626271752 |
| 6 | 7 | 0.007812658953 |
| 7 | 8 | 0.003906269871 |
| 8 | 9 | 0.001953127388 |
| 9 | 10 | 0.000976562732 |
| 10 | 11 | 0.000488281268 |
| 11 | 12 | 0.000244140626 |
| 12 | 13 | 0.000122070312 |
| 13 | 14 | 0.000061035156 |
| 14 | 15 | 0.000030517578 |
| 15 | 16 | 0.000015258789 |

These two LUTs will be included as a ROM internal to the CORDIC engine.

---

### Division (Linear Vectoring Mode)

#### Iteration Equations

For step $i$, the rotational direction is determined by $\sigma_i = \text{sign}(y_i)$:

$$\begin{aligned} x_{i+1} &= x_i \\ y_{i+1} &= y_i - \sigma_i \cdot (x_i \cdot 2^{-i}) \\ z_{i+1} &= z_i + \sigma_i \cdot 2^{-i} \end{aligned}$$

#### Input Pre-Normalization

* **Condition:** Linear vectoring requires $\vert{}y_0\vert{} \le \vert{}x_0\vert{}$ and $x_0 > 0$ to prevent accumulation overflow and guarantee convergence.
* **Method:** Shift $y_0$ right (or $x_0$ left) by $k$ bits until the condition is met:

$$y_0' = y_0 \cdot 2^{-k}$$


#### Post-Reversion

Shift the accumulated quotient register $z_N$ left by $k$ bits to restore the original scaling factor:


$$z_{\text{out}} = z_N \cdot 2^k$$

#### Post-Scaling

**None.** Linear mode does not introduce pseudo-rotation magnitude growth ($A_{\text{linear}} = 1.0$).

---

### Cosine (Circular Rotation Mode)

#### Iteration Equations

For step $i$, the rotational direction is determined by $\sigma_i = \text{sign}(z_i)$:

$$\begin{aligned} x_{i+1} &= x_i - \sigma_i \cdot (y_i \cdot 2^{-i}) \\ y_{i+1} &= y_i + \sigma_i \cdot (x_i \cdot 2^{-i}) \\ z_{i+1} &= z_i - \sigma_i \cdot \arctan(2^{-i}) \end{aligned}$$

#### Input Pre-Normalization

* **Condition:** The target angle $z_0$ must fall within the circular convergence range $\vert{}z_0\vert{} \le 1.7433 \text{ rad } (\approx 99.8^\circ)$.
* **Method:** Map the target angle $z_0$ into Quadrant I or IV ($[-\pi/2, \pi/2]$):

$$\begin{aligned}     \text{If } z_0 > \frac{\pi}{2}: & \quad z_0' = z_0 - \pi \\     \text{If } z_0 < -\frac{\pi}{2}: & \quad z_0' = z_0 + \pi     \end{aligned}$$

#### Post-Reversion

If a $\pm \pi$ angle shift was applied during pre-normalization, invert the final output signs:


$$x_{\text{out}} = -x_N, \quad y_{\text{out}} = -y_N$$

#### Post-Scaling

Circular pseudo-rotations expand the vector magnitude by $A \approx 1.64676$.

Initialize $x_0 = 1.0$ and multiply the final output $x_N$ by $1/A$.

---

### Vector Magnitude (Circular Vectoring Mode)

> **Note on 3D Vectors:** This CORDIC core natively calculates 2D vector magnitude ($\sqrt{x^2 + y^2}$). To compute a 3D magnitude ($\sqrt{x^2 + y^2 + z_{\text{space}}^2}$), run the 2D operation twice sequentially:
> 1. Pass $(x, y)$ to compute $M_1 = \sqrt{x^2 + y^2}$.
> 2. Pass $(M_1, z_{\text{space}})$ to compute $M_{\text{3D}} = \sqrt{M_1^2 + z_{\text{space}}^2}$.
>  

#### Iteration Equations

For step $i$, the rotational direction is determined by $\sigma_i = \text{sign}(y_i)$:

$$\begin{aligned} x_{i+1} &= x_i + \sigma_i \cdot (y_i \cdot 2^{-i}) \\ y_{i+1} &= y_i - \sigma_i \cdot (x_i \cdot 2^{-i}) \\ z_{i+1} &= z_i + \sigma_i \cdot \arctan(2^{-i}) \end{aligned}$$

#### Input Pre-Normalization

* **Condition:** The input vector must lie in Quadrant I or IV ($x_0 > 0$).
* **Method:** Take the absolute value of $x_0$ and $y_0$:

$$x_0' = \vert{}x_0\vert{}, \quad y_0' = \vert{}y_0\vert{}$$


#### Post-Reversion

**None.** Magnitude is rotationally invariant ($\sqrt{(-x)^2 + (-y)^2} = \sqrt{x^2 + y^2}$).

#### Post-Scaling

Multiply the final output $x_N$ by $1/A \approx 0.60725$ to remove the circular CORDIC gain:


$$\text{Magnitude} = x_N \cdot \frac{1}{A}$$

---

### Square Root (Hyperbolic Vectoring Mode)

#### Shift Index ($i$) Update Rule

Unlike circular or linear modes where the shift index $i$ equals the step index $j$, hyperbolic mode requires repeated iterations at $i \in \{4, 13, 40, 121, \dots\}$ to guarantee mathematical convergence.

Starting at $i_0 = 1$ for step $j = 0$, the next shift index $i_{j+1}$ is computed as:

$$i_{j+1} = \begin{cases} i_j & \text{if } i_j \in \{4, 13, 40, \dots\} \text{ and step } j \text{ is the first occurrence of } i_j \\ i_j + 1 & \text{otherwise} \end{cases}$$

#### Iteration Equations

To calculate $\sqrt{w}$, initialize $x_0 = w' + 0.25$, $y_0 = w' - 0.25$, and $z_0 = 0$. For step $j$, set the direction $\sigma_j = \text{sign}(y_j)$:

$$\begin{aligned} x_{i+1} &= x_i - \sigma_i \cdot (y_i \cdot 2^{-i_j}) \\ y_{i+1} &= y_i - \sigma_i \cdot (x_i \cdot 2^{-i_j}) \\ z_{i+1} &= z_i + \sigma_i \cdot \tanh^{-1}(2^{-i_j}) \end{aligned}$$


*(Note: $z$ is technically calculated here but is unused for the final square root result).*

#### Input Pre-Normalization

* **Condition:** The argument $w$ must be normalized to fit the tight hyperbolic convergence domain $w' \in [0.5, 2.0)$.
* **Method:** Factor out an even power of 2 ($2^{2k}$) using a bit shifter:

$$w' = w \cdot 2^{-2k}$$

Initialize the $x$ and $y$ registers with the normalized $w'$:

$$x_0 = w' + 0.25, \quad y_0 = w' - 0.25$$


#### Post-Reversion

Shift the output $x_N$ left by $k$ bits to account for the input pre-scaling ($\sqrt{w} = \sqrt{w' \cdot 2^{2k}} = \sqrt{w'} \cdot 2^k$):


$$x_{\text{rev}} = x_N \cdot 2^k$$

#### Post-Scaling

Hyperbolic CORDIC introduces a specific hyperbolic gain factor $A_h \approx 0.82816$. Multiply $x_{\text{rev}}$ by $1/A_h \approx 1.2075$:

---

$$\sqrt{w} = x_{\text{rev}} \cdot \frac{1}{A_h}$$

## Timing Overview

Below is a table detailing the number of cycles required for each operation:

| Operation | Pre-Normalization | CORDIC Loop | Post-Reversion | Gain Removal | Max Total Latency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Cosine ($\cos$)** | 1 cycle | $N$ cycles | 1 cycle | 0 cycles | $N + 2$ cycles |
| **Vector Magnitude** | 1 cycle | $N$ cycles | 0 cycles | 1 to 2 cycles | $N + 2$ to $N + 3$ cycles |
| **Division** | 1 cycle | $N$ cycles | 0 cycles | 0 cycles | $N + 1$ cycles |
| **Square Root** | 1 to 2 cycles | $N + R$ cycles | 1 cycle | 1 to 2 cycles | $N + R + 3$ to $N + R + 5$ cycles |
