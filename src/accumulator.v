`default_nettype none
`include "tinytracer_defs.vh"

module accumulator (
    input  wire                      clk,
    input  wire                      rst_n,

    ////////////////////////////////////
    //  RTU -> Accumulator Interface  //
    ////////////////////////////////////

    // Sample Request Channel
    input  wire                      sample_req_valid,   
    input  wire [3*`COLOR_DEPTH-1:0] sample_req_color, 
    output reg                       sample_req_ready,

    ////////////////////////////////////
    //  Accumulator -> I/O Interface  //
    ////////////////////////////////////

    // Pixel Request Channel
    output reg                       pixel_req_valid,    
    output reg  [3*`COLOR_DEPTH-1:0] pixel_req_color,
    input  wire                      pixel_req_ready
);

endmodule
