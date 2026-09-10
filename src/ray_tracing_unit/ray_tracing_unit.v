`default_nettype none
`include "tinytracer_defs.vh"

module rtu (
    input  wire                       clk,
    input  wire                       rst_n,

    input  wire                       render,

    //////////////////////////////
    //  RTU <-> SRAM Interface  //
    //////////////////////////////

    // SRAM Read Request Channel
    output reg                        sram_req_valid,
    output reg  [`ADDR_WIDTH-1:0]     sram_req_raddr,
    input  wire                       sram_req_ready,

    // SRAM Read Response Channel
    input  wire                       sram_resp_valid,
    input  wire [`DATA_WIDTH-1:0]     sram_resp_rdata,
    output reg                        sram_resp_ready,

    ////////////////////////////////
    //  RTU <-> Decode Interface  //
    ////////////////////////////////

    // Macro-op Request Channel
    output wire                       macro_req_valid,
    output wire [`MACRO_W-1:0]        macro_req_op,
    input  wire                       macro_req_ready,
    
    // Macro-op Response Channel
    input  wire                       macro_resp_valid,
    input  wire [3*`WLEN-1:0]         macro_resp_result,
    output wire                       macro_resp_ready,

    ////////////////////////////////////
    //  RTU -> Accumulator Interface  //
    ////////////////////////////////////

    // Sample Request Channel
    output reg                        sample_req_valid,   
    output reg  [3*`COLOR_DEPTH-1:0]  sample_req_color, 
    input  wire                       sample_req_ready
);

endmodule

