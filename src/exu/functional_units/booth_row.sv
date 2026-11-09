`default_nettype none

// ---------------------------------------------------------------------------
// Radix-4 Booth partial-product generator, used by booth_mul16.
// Plain Verilog-2005 syntax: reads the same as .v or .sv.
//
// The recoding table, as equations:
//
//   w    | neg two one | row
//   000  |  0   0   0  |  0
//   001  |  0   0   1  | +A
//   010  |  0   0   1  | +A
//   011  |  0   1   0  | +2A
//   100  |  1   1   0  | -2A
//   101  |  1   0   1  | -A
//   110  |  1   0   1  | -A
//   111  |  0   0   0  |  0   (neg low: no all-ones row + 1)
//
// Written as a `case`, Yosys infers a ROM and pulls the operand flops into
// its read port (21 extra flops in the TT top). Equations avoid that.
//
// 17 bits is enough: the negation's +1 is not added here, it goes to the
// tree as `neg`, and ~(2A) fits in 17 bits even for A = -32768.
// ---------------------------------------------------------------------------
module booth_row (
  input  wire [15:0] a,      // multiplicand
  input  wire [2:0]  w,      // {b[2i+1], b[2i], b[2i-1]}
  output wire [16:0] r,      // r[16] is the row's sign
  output wire        neg     // +1 to add at column 2i
);
  wire        one, two;
  wire [16:0] a1, a2;

  assign one = w[1] ^ w[0];
  assign two = (~w[2] & w[1] & w[0]) | (w[2] & ~w[1] & ~w[0]);
  assign neg = w[2] & ~(w[1] & w[0]);

  assign a1 = {a[15], a};     //  A, sign-extended one bit
  assign a2 = {a, 1'b0};      // 2A
  assign r  = (({17{one}} & a1) | ({17{two}} & a2)) ^ {17{neg}};
endmodule
