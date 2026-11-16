# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

# Reference model for clkdiv.
#
# Each cycle we add b or c to the 8-bit accumulator, depending on its MSB.
# q toggles on the edge where the MSB is already set, same as src/io/clkdiv.sv.


class ClkdivRef:
    # b is positive, c is negative. Both are stored as unsigned 8-bit values
    # (c = -18 is stored as 238).

    def __init__(self, b: int, c: int) -> None:
        self.b = b & 0xFF
        self.c = c & 0xFF
        self.sr = 0  # 8-bit accumulator
        self.q = 0   # output
        self._validate_params()

    def _validate_params(self) -> None:
        # The divider only works for these ranges, so catch bad settings early.
        c_signed = self.c if self.c < 128 else self.c - 256
        b_signed = self.b if self.b < 128 else self.b - 256

        assert b_signed > 0, f"b must be > 0, got {b_signed}"
        assert c_signed < 0, f"c must be < 0, got {c_signed}"
        assert b_signed >= -c_signed, f"b ({b_signed}) must be >= -c ({-c_signed})"
        assert (b_signed - c_signed) <= 127, f"b - c must be <= 127, got {b_signed - c_signed}"

    def set_params(self, b: int, c: int) -> None:
        # Change b and c but keep the accumulator and output, like the RTL does
        # when the inputs change mid-run.
        self.b = b & 0xFF
        self.c = c & 0xFF
        self._validate_params()

    def tick(self) -> int:
        # One clock cycle. Returns the output after the cycle.
        msb_was_set = self.sr & 0x80
        d = self.b if msb_was_set else self.c
        self.sr = (self.sr + d) & 0xFF
        if msb_was_set:
            self.q ^= 1
        return self.q

    def measure_frequency(self, cycles: int) -> float:
        # Count toggles over N cycles and return the frequency ratio.
        toggles = 0
        for _ in range(cycles):
            prev_q = self.q
            self.tick()
            if self.q != prev_q:
                toggles += 1

        return (toggles / 2) / cycles if cycles > 0 else 0.0
