`default_nettype none
`include "tinytracer_defs.vh"

module functional_units (
    input  wire                       clk,
    input  wire                       rst_n,

    ///////////////////////////////
    //  Decode <-> FU Interface  //
    ///////////////////////////////

    // Register File Port
    output reg                        reg_wen,
    output reg  [2:0]                 reg_addr,
    output reg  [`WLEN-1:0]           reg_wdata,
    input  wire [`WLEN-1:0]           reg_rdata,

    // Micro-op Request Channel
    input  wire                       micro_req_valid,
    input  wire [`MICRO_W-1:0]        micro_req_op,
    output reg                        micro_req_ready,

    // Micro-op Response Channel
    output reg                        micro_resp_done,

    /////////////////////////////////
    //  CORDIC <-> SRAM Interface  //
    /////////////////////////////////

    // SRAM Read Request Channel
    output wire                       sram_req_valid,
    output wire [`ADDR_WIDTH-1:0]     sram_req_raddr,
    input  wire                       sram_req_ready,

    // SRAM Read Response Channel
    input  wire                       sram_resp_valid,
    input  wire [`WLEN-1:0]           sram_resp_rdata,
    output wire                       sram_resp_ready
);

endmodule
