`default_nettype none
`include "tinytracer_defs.vh"

module alu (
    input  wire             clk,
    input  wire             rst_n,    
    
    ////////////////////////////
    //  FU <-> ALU Interface  //
    ////////////////////////////

    // Micro-op Request Channel
    input  wire             micro_req_valid,
    input  wire [`WLEN-1:0] micro_req_op1,          
    input  wire [`WLEN-1:0] micro_req_op2,
    input  wire [2:0]       micro_req_opcode,
    output reg              micro_req_ready,

    // Micro-op Response Channel
    output reg              micro_resp_done,
    output reg  [`WLEN-1:0] micro_resp_result
);

endmodule
