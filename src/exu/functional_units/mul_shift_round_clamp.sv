`default_nettype none

// ---------------------------------------------------------------------------
// Fixed-point multiply, signed 16 x 16 -> 16, purely combinational.
// The datapath of `multiplier`. Plain Verilog-2005 syntax, like booth_mul16.
//
//   p      = a * b                        full 32-bit product (booth_mul16)
//   s      = dir ? 14 : 7                 dir is the FMT bit
//   r      = (p + 2^(s-1)) >> s           round half up, arithmetic shift
//   result = r, or 16'h7FFF / 16'h8000 if r does not fit in 16 bits
//
//   dir = 0 (FMT_POS): POS x POS -> POS     14 -> 7 fraction bits
//   dir = 1 (FMT_DIR): POS x DIR -> POS     21 -> 7
//                      DIR x DIR -> DIR     28 -> 14
//
// Rounding: (p + 2^(s-1)) >> s == (p >> s) + p[s-1], so it is one increment
// of the kept bits, not a 32-bit add. Halves round up (towards +infinity):
// +0.5 LSB -> 1, -0.5 LSB -> 0.
// ---------------------------------------------------------------------------
module mul_shift_round_clamp (
  input  wire [15:0] a,
  input  wire [15:0] b,
  input  wire        dir,     // FMT: 0 = shift right 7, 1 = shift right 14
  output wire [15:0] result
);
  wire [31:0] p;

  booth_mul16 u_booth (.a(a), .b(b), .p(p));

  // p >> s, sign-extended to 25 bits, and the bit just below the result's LSB
  wire [24:0] kept = dir ? {{7{p[31]}}, p[31:14]} : p[31:7];
  wire        half = dir ? p[13] : p[6];

  // Round. Cannot overflow 25 bits: |p| <= 2^30, so |p >> 7| <= 2^23.
  wire [24:0] r = kept + {24'b0, half};

  // r fits in 16 bits when bits 24..15 are all copies of the sign bit
  wire fits = (r[24:15] == {10{r[15]}});

  assign result = fits ? r[15:0] : (r[24] ? 16'h8000 : 16'h7FFF);

  // Bits below the rounding bit never reach the result
  wire _unused = &{1'b0, p[5:0]};
endmodule
