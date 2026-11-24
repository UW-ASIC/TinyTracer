`default_nettype none

module tb_sram_control
  import tinytracer_pkg::*;
(
  input  logic                  clk,
  input  logic                  rst_n,

  // I/O write channel (flattened)
  input  logic                  io_wr_req_wen,
  input  logic [ADDR_WIDTH-1:0] io_wr_req_waddr,
  input  logic [DATA_WIDTH-1:0] io_wr_req_wdata,
  input  logic                  io_wr_req_valid,
  output logic                  io_wr_req_ready,

  // RTU read channel (flattened)
  input  logic [ADDR_WIDTH-1:0] rtu_rd_req_raddr,
  input  logic                  rtu_rd_req_valid,
  output logic                  rtu_rd_req_ready,
  output logic [DATA_WIDTH-1:0] rtu_rd_resp_rdata,
  output logic                  rtu_rd_resp_valid,
  input  logic                  rtu_rd_resp_ready,

  // SRAM side
  output logic                  wen,
  output logic [ADDR_WIDTH-1:0] addr,
  output logic [DATA_WIDTH-1:0] din,
  input  logic [DATA_WIDTH-1:0] dout
);

  // The two "cables"
  sram_wr_if io_wr();
  sram_rd_if rtu_rd();

  // Testbench -> cables (what the client end would drive)
  assign io_wr.req_wen     = io_wr_req_wen;
  assign io_wr.req_waddr   = io_wr_req_waddr;
  assign io_wr.req_wdata   = io_wr_req_wdata;
  assign io_wr.req_valid   = io_wr_req_valid;
  assign rtu_rd.req_raddr  = rtu_rd_req_raddr;
  assign rtu_rd.req_valid  = rtu_rd_req_valid;
  assign rtu_rd.resp_ready = rtu_rd_resp_ready;

  // Cables -> testbench (what the server end drives)
  assign io_wr_req_ready   = io_wr.req_ready;
  assign rtu_rd_req_ready  = rtu_rd.req_ready;
  assign rtu_rd_resp_rdata = rtu_rd.resp_rdata;
  assign rtu_rd_resp_valid = rtu_rd.resp_valid;

  // The design under test
  sram_control u_dut (
    .clk    (clk),
    .rst_n  (rst_n),
    .io_wr  (io_wr),
    .rtu_rd (rtu_rd),
    .wen    (wen),
    .addr   (addr),
    .din    (din),
    .dout   (dout)
  );

endmodule
