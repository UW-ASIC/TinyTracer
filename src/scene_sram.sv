`default_nettype wire

// Single-port 512 x 16 scene SRAM, driven by sram_control. A write, or the
// read of addr onto dout, takes effect at the rising clock edge.
// Simulation uses the behavioural model below. Synthesis will instantiate
// the SRAM macro here; until that is decided, synthesis ties dout to 0 so
// that the flow does not build the memory out of flip-flops.
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
    dout <= mem[addr];
  end
`else
  assign dout = '0;
`endif

endmodule
