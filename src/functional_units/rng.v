`default_nettype none
`include "tinytracer_defs.vh"

module xorshift_rng #(
    parameter   [`WLEN-1:0] SEED = 16'hACE1 // If word length ever changes from 16, use a different seed of length WLEN
) (
    input  wire             clk,
    input  wire             rst_n,    
    
    ////////////////////////////
    //  FU <-> RNG Interface  //
    ////////////////////////////

    // Micro-op Request Channel
    input  wire             micro_req_valid,
    output reg              micro_req_ready,

    // Micro-op Response Channel
    output reg              micro_resp_done,
    output reg  [`WLEN-1:0] micro_resp_result
);

endmodule
