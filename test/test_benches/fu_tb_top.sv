`default_nettype wire

module fu_tb_top (
    input  logic        clk,
    input  logic        rst_n,

    // Micro-op Channel
    input  logic        micro_req_valid,
    input  logic [12:0] micro_req_op,
    input  logic        micro_req_fmt,
    input  logic        micro_req_direct,
    input  logic [15:0] micro_req_u1,
    input  logic [15:0] micro_req_v1,
    output logic        micro_req_ready,
    output logic        micro_resp_done,

    // Register File Load
    input  logic        rf_load,
    input  logic [47:0] rf_load_u,
    input  logic [47:0] rf_load_v,

    // Register File Ports
    output logic        rf_wen,
    output logic [ 2:0] rf_waddr,
    output logic [15:0] rf_wdata,
    output logic [ 2:0] rf_raddr1,
    output logic [ 2:0] rf_raddr2
);

  micro_if micro ();

  assign micro.req_valid  = micro_req_valid;
  assign micro.req_op     = micro_req_op;
  assign micro.req_fmt    = tinytracer_pkg::fmt_t'(micro_req_fmt);
  assign micro.req_direct = micro_req_direct;
  assign micro.req_u1     = micro_req_u1;
  assign micro.req_v1     = micro_req_v1;
  assign micro_req_ready  = micro.req_ready;
  assign micro_resp_done  = micro.resp_done;

  logic [15:0] rf_rdata1;
  logic [15:0] rf_rdata2;
  tinytracer_pkg::vec3_t rf_result;

  reg_file u_reg_file (
      .clk   (clk),
      .rst_n (rst_n),
      .load  (rf_load),
      .load_u(rf_load_u),
      .load_v(rf_load_v),
      .result(rf_result),
      .wen   (rf_wen),
      .waddr (rf_waddr),
      .wdata (rf_wdata),
      .raddr1(rf_raddr1),
      .rdata1(rf_rdata1),
      .raddr2(rf_raddr2),
      .rdata2(rf_rdata2)
  );

  fu_control dut (
      .clk      (clk),
      .rst_n    (rst_n),
      .rf_wen   (rf_wen),
      .rf_waddr (rf_waddr),
      .rf_wdata (rf_wdata),
      .rf_raddr1(rf_raddr1),
      .rf_rdata1(rf_rdata1),
      .rf_raddr2(rf_raddr2),
      .rf_rdata2(rf_rdata2),
      .micro    (micro)
  );

endmodule
