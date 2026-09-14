`default_nettype none
`include "tinytracer_defs.vh"

module shader_core (
    input  wire                            clk,
    input  wire                            rst_n,

    input  wire [3*`COLOR_DEPTH-1:0]       sky_color,
    input  wire [3*`COLOR_DEPTH-1:0]       object_color,
    input  wire [1:0]                      mat_type,
    input  wire [$clog2(`MAX_BOUNCES)-1:0] ray_bounces_left,
    input  wire                            hit,

    ////////////////////////////////////
    //  RTU -> Accumulator Interface  //
    ////////////////////////////////////

    // Sample Request Channel
    output reg                             sample_req_valid,   
    output reg [3*`COLOR_DEPTH-1:0]        sample_req_color, 
    input  wire                            sample_req_ready,

    ////////////////////////////////
    //  RTU <-> Decode Interface  //
    ////////////////////////////////

    // Macro-op Request Channel
    output wire                            macro_req_valid,
    output wire [`MACRO_W-1:0]             macro_req_op,
    input  wire                            macro_req_ready,
    
    // Macro-op Response Channel
    output wire                            macro_resp_ready,
    input  wire                            macro_resp_valid,
    input  wire [3*`WLEN-1:0]              macro_resp_result
);

endmodule