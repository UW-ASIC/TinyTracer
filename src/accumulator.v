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
    input  wire [3*`COLOUR_DEPTH-1:0] sample_req_colour, 
    output reg                       sample_req_ready,

    ////////////////////////////////////
    //  Accumulator -> I/O Interface  //
    ////////////////////////////////////

    // Pixel Request Channel
    output reg                       pixel_req_valid,    
    output reg  [3*`COLOUR_DEPTH-1:0] pixel_req_colour,
    input  wire                      pixel_req_ready
);

endmodule
