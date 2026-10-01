`default_nettype wire

// Reads and writes the RTU's shared header and ray state registers; the
// signals for that and for operand source selects are not defined yet (see
// docs/modules/rtu/rtu.md, Handshakes).
module ray_generator (
    input  logic                            clk,
    input  logic                            rst_n,

    // Controller <-> Ray Generator Signals (start, done: one-cycle pulses)
    input  logic                            start,           // Start signal from the Controller; mode valid with it
    input  logic                            mode,            // mode = 0 for primary ray generation, 1 otherwise
    output logic                            done,            // New ray is in the ray state registers

    // LFSR state, the request path's LFSR operand source. The RNG advances in
    // each cycle a request field is written from it.
    output logic [tinytracer_pkg::WLEN-1:0]                 rand_num,

    // Ray Generator <-> RTU Request Path Interface
    rtu_req_if.client                       req
);

  logic rng_req;  // advance the LFSR by 16 steps at the end of the cycle

  rng u_rng (
      .clk      (clk),
      .rst_n    (rst_n),
      .req      (rng_req),
      .rand_num (rand_num)
  );

endmodule
