`default_nettype none
`include "tinytracer_defs.vh"

module decode (
    input  wire                clk,
    input  wire                rst_n,

    ////////////////////////////////
    //  RTU <-> Decode Interface  //
    ////////////////////////////////

    // Macro-op Request Channel
    input wire                 macro_req_valid,
    input wire [`MACRO_W-1:0]  macro_req_op,
    output  wire               macro_req_ready,
    
    // Macro-op Response Channel
    output  wire               macro_resp_valid,
    output  wire [3*`WLEN-1:0] macro_resp_result, 
    input wire                 macro_resp_ready,

    ///////////////////////////////
    //  Decode <-> FU Interface  //
    ///////////////////////////////

    // Micro-op Request Channel
    output reg                 micro_req_valid,
    output reg [`MICRO_W-1:0]  micro_req_op,        
    input  wire                micro_req_ready,

    // Micro-op Response Channel
    input  wire                micro_resp_done,

    // Register File Port
    output reg                 reg_wen,
    output reg  [2:0]          reg_addr,
    output reg  [`WLEN-1:0]    reg_wdata,
    input  wire [`WLEN-1:0]    reg_rdata
);

endmodule
