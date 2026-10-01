`default_nettype wire

// Execution Unit: wraps Decode (with its micro-op ROM), the register file, and
// FU Control with its functional units. The macro-op channel is the only
// external interface and passes through to Decode.
module exu (
    input  logic        clk,
    input  logic        rst_n,

    // RTU <-> EXU Interface
    macro_if.server     macro
);

  // Decode <-> FU Control Interface
  micro_if micro ();

  // Macro-op operands, copied out of the interface so the struct fields can
  // be selected
  tinytracer_pkg::macro_word_t macro_req_op;
  assign macro_req_op = macro.req_op;

  // Register file ports
  logic                  rf_load;
  tinytracer_pkg::vec3_t rf_result;
  logic                  rf_wen;
  logic [2:0]            rf_waddr;
  logic [tinytracer_pkg::WLEN-1:0]       rf_wdata;
  logic [2:0]            rf_raddr1;
  logic [tinytracer_pkg::WLEN-1:0]       rf_rdata1;
  logic [2:0]            rf_raddr2;
  logic [tinytracer_pkg::WLEN-1:0]       rf_rdata2;

  decode u_decode (
      .clk       (clk),
      .rst_n     (rst_n),
      .macro     (macro),
      .micro     (micro),
      .rf_load   (rf_load),
      .rf_result (rf_result)
  );

  // Decode loads the operands and reads the result in parallel; FU Control
  // owns the addressed ports.
  reg_file u_reg_file (
      .clk    (clk),
      .rst_n  (rst_n),
      .load   (rf_load),
      .load_u (macro_req_op.u),
      .load_v (macro_req_op.v),
      .result (rf_result),
      .wen    (rf_wen),
      .waddr  (rf_waddr),
      .wdata  (rf_wdata),
      .raddr1 (rf_raddr1),
      .rdata1 (rf_rdata1),
      .raddr2 (rf_raddr2),
      .rdata2 (rf_rdata2)
  );

  fu_control u_fu_control (
      .clk       (clk),
      .rst_n     (rst_n),
      .rf_wen    (rf_wen),
      .rf_waddr  (rf_waddr),
      .rf_wdata  (rf_wdata),
      .rf_raddr1 (rf_raddr1),
      .rf_rdata1 (rf_rdata1),
      .rf_raddr2 (rf_raddr2),
      .rf_rdata2 (rf_rdata2),
      .micro     (micro)
  );

endmodule
