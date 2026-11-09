`default_nettype none

// Radix-4 Booth multiplier, signed 16 x 16 -> 32, purely combinational.
// Plain Verilog-2005 syntax: reads the same as .v or .sv, with or without
// -g2012 / -sv.
//
//   booth_row    one partial-product generator (booth_row.sv)
//   csa          one 3:2 compressor row of the Wallace tree (csa.sv)
//   booth_mul16  8 windows of b -> 8 booth_row -> 7 csa -> final add
module booth_mul16 (
  input  wire signed [15:0] a,
  input  wire signed [15:0] b,
  output wire signed [31:0] p
);
  // ---- Partial-product generators: one per 3-bit window of b ----
  wire [16:0] r0, r1, r2, r3, r4, r5, r6, r7;
  wire [7:0]  neg;

  booth_row u_row0 (.a(a), .w({b[1:0], 1'b0}), .r(r0), .neg(neg[0]));
  booth_row u_row1 (.a(a), .w(b[3:1]),         .r(r1), .neg(neg[1]));
  booth_row u_row2 (.a(a), .w(b[5:3]),         .r(r2), .neg(neg[2]));
  booth_row u_row3 (.a(a), .w(b[7:5]),         .r(r3), .neg(neg[3]));
  booth_row u_row4 (.a(a), .w(b[9:7]),         .r(r4), .neg(neg[4]));
  booth_row u_row5 (.a(a), .w(b[11:9]),        .r(r5), .neg(neg[5]));
  booth_row u_row6 (.a(a), .w(b[13:11]),       .r(r6), .neg(neg[6]));
  booth_row u_row7 (.a(a), .w(b[15:13]),       .r(r7), .neg(neg[7]));

  // ---- Place the rows: row i at columns 2i .. 2i+16, sign bit inverted ----
  wire [31:0] pp0, pp1, pp2, pp3, pp4, pp5, pp6, pp7, extra;

  assign pp0 = {15'b0, ~r0[16], r0[15:0]        };
  assign pp1 = {13'b0, ~r1[16], r1[15:0],  2'b0};
  assign pp2 = {11'b0, ~r2[16], r2[15:0],  4'b0};
  assign pp3 = { 9'b0, ~r3[16], r3[15:0],  6'b0};
  assign pp4 = { 7'b0, ~r4[16], r4[15:0],  8'b0};
  assign pp5 = { 5'b0, ~r5[16], r5[15:0], 10'b0};
  assign pp6 = { 3'b0, ~r6[16], r6[15:0], 12'b0};
  assign pp7 = { 1'b0, ~r7[16], r7[15:0], 14'b0};

  // neg_i at column 2i (row i+1 starts at 2i+2, so the slot is free).
  // Above it the sign-extension constant -(2^16 + 2^18 + ... + 2^30) mod 2^32
  // = 0xAAAB0000: a 1 left of every inverted sign bit, plus one at column 16.
  assign extra = {16'hAAAB,
                  1'b0, neg[7], 1'b0, neg[6], 1'b0, neg[5], 1'b0, neg[4],
                  1'b0, neg[3], 1'b0, neg[2], 1'b0, neg[1], 1'b0, neg[0]};

  // ---- Wallace tree: 9 rows -> 6 -> 4 -> 3 -> 2 ----
  wire [31:0] s1a, c1a, s1b, c1b, s1c, c1c;
  wire [31:0] s2a, c2a, s2b, c2b;
  wire [31:0] s3, c3;
  wire [31:0] s4, c4;

  csa u_l1a (.x(pp0), .y(pp1), .z(pp2),   .s(s1a), .c(c1a));
  csa u_l1b (.x(pp3), .y(pp4), .z(pp5),   .s(s1b), .c(c1b));
  csa u_l1c (.x(pp6), .y(pp7), .z(extra), .s(s1c), .c(c1c));

  csa u_l2a (.x(s1a), .y(c1a), .z(s1b),   .s(s2a), .c(c2a));
  csa u_l2b (.x(c1b), .y(s1c), .z(c1c),   .s(s2b), .c(c2b));

  csa u_l3  (.x(s2a), .y(c2a), .z(s2b),   .s(s3),  .c(c3));    // c2b skips this level
  csa u_l4  (.x(s3),  .y(c3),  .z(c2b),   .s(s4),  .c(c4));

  // ---- Final carry-propagate add ----
  assign p = s4 + c4;
endmodule
