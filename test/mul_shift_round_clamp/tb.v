`default_nettype none
`timescale 1ns / 1ps

/* Testbench for the fixed-point multiply. It instantiates mul_shift_round_clamp and
   makes wires that test_mul_shift_round_clamp.py drives.
*/
module tb ();

  // Dump the testbench's own signals to a VCD file (gtkwave or surfer).
  // Depth 1 keeps the file small over 80,000 multiplies; use
  // $dumpvars(0, tb) to see inside the multiplier as well.
  initial begin
    $dumpfile("tb.vcd");
    $dumpvars(1, tb);
    #1;
  end

  reg  [15:0] a;
  reg  [15:0] b;
  reg         dir;     // FMT: 0 = shift right 7 (POS), 1 = shift right 14 (DIR)
  wire [15:0] result;

  mul_shift_round_clamp dut (
      .a     (a),
      .b     (b),
      .dir   (dir),
      .result(result)
  );

endmodule
