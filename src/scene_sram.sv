`default_nettype wire

// Single-port 512 x 16 scene SRAM, driven by sram_control. A write, or the
// read of addr onto dout, takes effect at the rising clock edge. A write
// cycle does not read: dout keeps its value.
// Simulation uses the behavioural model below. Synthesis instantiates IHP's
// RM_IHPSG13_1P_512x16_c2_bm_bist macro, whose views src/config.json gives
// the flow.
module scene_sram (
    input  logic                  clk,

    // SRAM Controller <-> SRAM Signals
    input  logic                  wen,   // write din to addr
    input  logic [tinytracer_pkg::ADDR_WIDTH-1:0] addr,
    input  logic [tinytracer_pkg::DATA_WIDTH-1:0] din,
    output logic [tinytracer_pkg::DATA_WIDTH-1:0] dout   // word at addr, from the previous edge
);

`ifndef SYNTHESIS
  logic [tinytracer_pkg::DATA_WIDTH-1:0] mem [0:(1<<tinytracer_pkg::ADDR_WIDTH)-1];

  always_ff @(posedge clk) begin
    if (wen) mem[addr] <= din;
    else     dout      <= mem[addr];
  end
`else
  // The macro reads when REN is high and writes when WEN is high; with both
  // high it writes din and returns it (write-through), so REN is ~wen. MEN
  // enables every cycle. The datasheet requires A_DLY = 1; A_BM all ones
  // writes the whole word; the BIST port is unused. keep stops synthesis
  // from removing the macro while nothing reads dout.
  (* keep *)
  RM_IHPSG13_1P_512x16_c2_bm_bist u_sram (
      .A_CLK       (clk),
      .A_MEN       (1'b1),
      .A_WEN       (wen),
      .A_REN       (~wen),
      .A_ADDR      (addr),
      .A_DIN       (din),
      .A_DLY       (1'b1),
      .A_DOUT      (dout),
      .A_BM        ({tinytracer_pkg::DATA_WIDTH{1'b1}}),
      .A_BIST_CLK  (1'b0),
      .A_BIST_EN   (1'b0),
      .A_BIST_MEN  (1'b0),
      .A_BIST_WEN  (1'b0),
      .A_BIST_REN  (1'b0),
      .A_BIST_ADDR ('0),
      .A_BIST_DIN  ('0),
      .A_BIST_BM   ('0)
  );
`endif

endmodule
