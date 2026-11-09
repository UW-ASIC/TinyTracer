`default_nettype none

// ---------------------------------------------------------------------------
// 3:2 carry-save adder on 32-bit rows: x + y + z == s + c (mod 2^32).
// One row of booth_mul16's Wallace tree.
// Plain Verilog-2005 syntax: reads the same as .v or .sv.
//
// One full adder per column: s is the column's sum bit, c its carry moved
// one column left. Nothing ripples between columns.
// ---------------------------------------------------------------------------
module csa (
  input  wire [31:0] x,
  input  wire [31:0] y,
  input  wire [31:0] z,
  output wire [31:0] s,
  output wire [31:0] c
);
  assign s = x ^ y ^ z;
  assign c = {(x[30:0] & y[30:0]) | (x[30:0] & z[30:0]) | (y[30:0] & z[30:0]), 1'b0};
endmodule
