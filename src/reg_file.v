`default_nettype none
`include "tinytracer_defs.vh"

module reg_file (
    input  wire                clk,
    input  wire                rst_n,

    // Single Read/Write Port
    input  wire [2:0]          addr,
    input  wire                wen,
    input  wire [`WLEN-1:0]    wdata,
    output reg  [`WLEN-1:0]    rdata
);

endmodule
