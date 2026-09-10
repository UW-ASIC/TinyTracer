`default_nettype none
`include "tinytracer_defs.vh"

module uart (
    input  wire       clk,
    input  wire       rst_n,

    /////////////////////////////
    //  UART <-> I/O Interface //
    /////////////////////////////
    
    // UART Request Channel
    output reg        uart_req_valid,
    output reg  [7:0] uart_req_data, // RX byte data
    input  wire       uart_req_ready,
    
    // UART Response Channel
    input  wire       uart_resp_valid,
    input  wire [7:0] uart_resp_data, // TX byte data
    output reg        uart_resp_ready,
     
    //////////////////////
    //  UART Interface  //
    //////////////////////

    input  wire       TT_RX,
    output reg        TT_TX
);

endmodule
