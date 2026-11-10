`default_nettype none
`timescale 1ns / 1ps

module tb_shader_core ();
  localparam ADDR_WIDTH = 9;
  localparam WLEN       = 16;
  localparam DATA_WIDTH = 16;

  logic                   clk;
  logic                   rst_n;
  logic                   new_sample;
  logic                   start;
  logic                   hit;
  logic                   hit_ground;
  logic [ADDR_WIDTH-1:0]  hit_addr;
  logic                   last_bounce;
  logic                   done;
  logic                   path_end;
  logic [1:0]             material;
  logic [35:0]            sample;
  logic [47:0]            ray_origin;
  logic [47:0]            ray_dir;
  logic [23:0]            sky_horizon;
  logic [23:0]            sky_top;
  logic [23:0]            ground_a;
  logic [23:0]            ground_b;
  logic [ADDR_WIDTH-1:0]  sram_addr;
  logic                   sram_rd;
  logic [DATA_WIDTH-1:0]  sram_data;
  logic                   sram_valid;
  logic                   req_valid;
  logic [101:0]           req_op;
  logic                   req_ready;
  logic                   resp_valid;
  logic [3*WLEN-1:0]      resp_result;
  logic                   resp_ready;

  shader_core #(
      .ADDR_WIDTH(ADDR_WIDTH),
      .WLEN      (WLEN),
      .DATA_WIDTH(DATA_WIDTH)
  ) u1 (
      .clk        (clk),
      .rst_n      (rst_n),
      .new_sample (new_sample),
      .start      (start),
      .hit        (hit),
      .hit_ground (hit_ground),
      .hit_addr   (hit_addr),
      .last_bounce(last_bounce),
      .done       (done),
      .path_end   (path_end),
      .material   (material),
      .sample     (sample),
      .ray_origin (ray_origin),
      .ray_dir    (ray_dir),
      .sky_horizon(sky_horizon),
      .sky_top    (sky_top),
      .ground_a   (ground_a),
      .ground_b   (ground_b),
      .sram_addr  (sram_addr),
      .sram_rd    (sram_rd),
      .sram_data  (sram_data),
      .sram_valid (sram_valid),
      .req_valid  (req_valid),
      .req_op     (req_op),
      .req_ready  (req_ready),
      .resp_valid (resp_valid),
      .resp_result(resp_result),
      .resp_ready (resp_ready)
  );

endmodule
