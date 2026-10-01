/*
 * Copyright (c) 2026 University of Waterloo ASIC Design Team
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype wire

// Top level: wires the I/O Unit, SRAM controller and SRAM, RTU, EXU, and
// Accumulator together through the interfaces in tinytracer_if.sv. See
// docs/modules/tt_um_tinytracer.md.
module tt_um_tinytracer (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  ///////////////////////////
  //  Top-Level Interfaces //
  ///////////////////////////

  render_if                     render_cmd (); // I/O -> RTU: render strobe, image size
  sram_wr_if                    sram_wr ();    // I/O -> SRAM controller: scene writes
  sram_rd_if                    sram_rd ();    // RTU <-> SRAM controller: scene reads
  macro_if                      macro ();      // RTU <-> EXU: macro-ops
  colour_if #(.W(tinytracer_pkg::SAMPLE_DEPTH)) sample ();     // RTU -> Accumulator: sample colours
  colour_if #(.W(tinytracer_pkg::COLOUR_DEPTH)) pixel ();      // Accumulator -> I/O: pixel colours

  logic [tinytracer_pkg::SPP_LOG2_W-1:0] spp_log2;             // RTU -> Accumulator: log2(samples per pixel)

  // SRAM controller <-> SRAM
  logic                  sram_wen;
  logic [tinytracer_pkg::ADDR_WIDTH-1:0] sram_addr;
  logic [tinytracer_pkg::DATA_WIDTH-1:0] sram_din;
  logic [tinytracer_pkg::DATA_WIDTH-1:0] sram_dout;

  logic                  uart_tx;

  /////////////////
  //  Instances  //
  /////////////////

  // clkdiv_ctl and clkdiv_data have no pins yet; 2'b00 means "do nothing".
  io u_io (
      .clk         (clk),
      .rst_n       (rst_n),
      .clkdiv_ctl  (2'b00),
      .clkdiv_data (8'h00),
      .render      (render_cmd),
      .uart_rx     (ui_in[3]),
      .uart_tx     (uart_tx),
      .pixel       (pixel),
      .sram        (sram_wr)
  );

  sram_control u_sram_control (
      .clk    (clk),
      .rst_n  (rst_n),
      .io_wr  (sram_wr),
      .rtu_rd (sram_rd),
      .wen    (sram_wen),
      .addr   (sram_addr),
      .din    (sram_din),
      .dout   (sram_dout)
  );

  scene_sram u_scene_sram (
      .clk  (clk),
      .wen  (sram_wen),
      .addr (sram_addr),
      .din  (sram_din),
      .dout (sram_dout)
  );

  rtu u_rtu (
      .clk      (clk),
      .rst_n    (rst_n),
      .render   (render_cmd),
      .sram     (sram_rd),
      .macro    (macro),
      .sample   (sample),
      .spp_log2 (spp_log2)
  );

  exu u_exu (
      .clk   (clk),
      .rst_n (rst_n),
      .macro (macro)
  );

  accumulator u_accumulator (
      .clk      (clk),
      .rst_n    (rst_n),
      .sample   (sample),
      .spp_log2 (spp_log2),
      .pixel    (pixel)
  );

  ////////////
  //  Pins  //
  ////////////

  // ui_in[3] = uart_rx, uo_out[4] = uart_tx (info.yaml). The bidirectional
  // pins are unused inputs.
  assign uo_out  = {3'b000, uart_tx, 4'b0000};
  assign uio_out = 8'h00;
  assign uio_oe  = 8'h00;

  // List all unused inputs to prevent warnings
  wire _unused = &{ena, ui_in[7:4], ui_in[2:0], uio_in, 1'b0};

endmodule
