`default_nettype none
`include "tinytracer_defs.vh"

module io (
    input  wire                      clk,
    input  wire                      rst_n,
    
    output reg                       render,         // One-cycle pulse to RTU when a RENDER message is parsed
    
    /////////////////////////////
    //  UART <-> I/O Interface //
    /////////////////////////////
    
    // UART Request Channel
    input  wire                      uart_req_valid, 
    input  wire [7:0]                uart_req_data,
    output reg                       uart_req_ready,
    
    // UART Response Channel
    output reg                       uart_resp_valid,
    output reg  [7:0]                uart_resp_data,
    input  wire                      uart_resp_ready,

    ////////////////////////////////////
    //  Accumulator -> I/O Interface  //
    ////////////////////////////////////

    // Pixel Request Channel
    input  wire                      pixel_req_valid,    
    input  wire [3*`COLOR_DEPTH-1:0] pixel_req_color,
    output reg                       pixel_req_ready,        

    ///////////////////////////
    // I/O -> SRAM Interface //
    ///////////////////////////

    // SRAM Write Request Channel
    output reg                       sram_req_valid,
    input  wire                      sram_req_ready,
    output reg                       sram_req_wen,
    output reg  [`ADDR_WIDTH-1:0]    sram_req_waddr,
    output reg  [`DATA_WIDTH-1:0]    sram_req_wdata
);

endmodule

