`default_nettype none
`include "tinytracer_defs.vh"

module xorshift_rng (
    input  wire             clk,
    input  wire             rst_n,    
    
    ////////////////////////////////
    //  FU <-> INVSQRT Interface  //
    ////////////////////////////////

    // Micro-op Request Channel
    input  wire             micro_req_valid,
    output reg              micro_req_ready,

    // Micro-op Response Channel
    output reg              micro_resp_done,
    output reg  [`WLEN-1:0] micro_resp_result
);

endmodule
