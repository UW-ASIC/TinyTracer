`default_nettype wire

module fu_control (
    input  logic        clk,
    input  logic        rst_n,

    // Register File Ports (both read ports for operands, write port for results)
    output logic            rf_wen,
    output logic [2:0]      rf_waddr,
    output logic [tinytracer_pkg::WLEN-1:0] rf_wdata,
    output logic [2:0]      rf_raddr1,
    input  logic [tinytracer_pkg::WLEN-1:0] rf_rdata1,
    output logic [2:0]      rf_raddr2,
    input  logic [tinytracer_pkg::WLEN-1:0] rf_rdata2,

    // Micro-op Channel (scalar macro-ops carry their operands on it instead
    // of using the read ports)
    micro_if.server     micro
);

  // FU Control <-> Functional Units
  fu_if fu_alu ();
  fu_if fu_mul ();
  fu_if fu_cordic ();

  alu u_alu (
      .clk   (clk),
      .rst_n (rst_n),
      .fu    (fu_alu)
  );

  multiplier u_multiplier (
      .clk   (clk),
      .rst_n (rst_n),
      .fu    (fu_mul)
  );

  cordic u_cordic (
      .clk   (clk),
      .rst_n (rst_n),
      .fu    (fu_cordic)
  );

endmodule
