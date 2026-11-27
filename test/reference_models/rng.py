# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0


# Reference Model for RNG module
# 16-bit Galois LFSR that resets to 1
# and advances 16 steps per req pulse, used to predict rand_num in the tests

class RngModel:
    def __init__(
        self, 
        width = 16, 
        taps = 0x100B,
        seed = 1
    ):
        self.width = width
        self.taps = taps
        self.mask = (1 << width) - 1 # 0xFFFF
        self.state = seed
    
    # One Galois step (Models a single clock of the LSFR)
    def step1(self):
        """One Galois step: shift left, XOR taps in if the MSB fell out."""
        msb = (self.state >> (self.width - 1)) & 1
        self.state = (self.state << 1) & self.mask
        if msb:
            # state <= state[msb] ? state_shifted ^ taps : state_shifted
            self.state ^= self.taps

    # One Request
    def request(self):
        """What one req pulse does: 16 steps. Returns the new state."""
        for _ in range(16):
            self.step1()
        return self.state

    # Reading output
    @property
    def rand_num(self):
        return self.state