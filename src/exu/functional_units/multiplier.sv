`default_nettype wire

// Fixed-point multiplier functional unit
// (docs/modules/exu/functional_units/multiplier.md).
//
// mul_shift_round_clamp does the arithmetic: radix-4 Booth product, shift right by 7
// (FMT_POS) or 14 (FMT_DIR), round half up, clamp to 16 bits. This module
// puts the fu_if handshake around it:
//   * req_ready is always 1: a new request can be accepted every cycle
//   * the result is registered: resp_done and resp_result come in the cycle
//     after the request is accepted, so the latency is 1 cycle
//   * req_opcode is ignored
//
//   mul_shift_round_clamp -> booth_mul16 -> booth_row x 8, csa x 7
module multiplier (
    input  logic        clk,
    input  logic        rst_n,

    // FU <-> Multiplier Interface
    fu_if.server        fu
);
  logic [15:0] result;
  logic        done_q;
  logic [15:0] result_q;

  mul_shift_round_clamp u_mul       (
      .a     (fu.req_op1),
      .b     (fu.req_op2),
      .dir   (fu.req_fmt == tinytracer_pkg::FMT_DIR),
      .result(result)
  );

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      done_q   <= 1'b0;
      result_q <= '0;
    end else begin
      done_q   <= fu.req_valid;  // req_ready is always 1, so valid means accepted
      result_q <= result;        // only read by FU Control when resp_done is high
    end
  end

  assign fu.req_ready   = 1'b1;
  assign fu.resp_done   = done_q;
  assign fu.resp_result = result_q;

  // The multiplier has one operation, so it does not use req_opcode
  logic _unused;
  assign _unused = &{1'b0, fu.req_opcode};
endmodule
