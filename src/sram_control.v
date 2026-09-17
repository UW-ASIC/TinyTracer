`default_nettype none
`include "tinytracer_defs.vh"

module sram_control (
    input  wire                               clk,
    input  wire                               rst_n,

    /////////////////////////////
    //  I/O -> SRAM Interface  //
    /////////////////////////////

    // SRAM Write Request Channel
    input  wire                               io_sram_req_valid,
    output reg                                io_sram_req_ready,
    input  wire                               io_sram_req_wen,
    input  wire [`ADDR_WIDTH-1:0]             io_sram_req_waddr,
    input  wire [`DATA_WIDTH-1:0]             io_sram_req_wdata,

    //////////////////////////////
    //  RTU <-> SRAM Interface  //
    //////////////////////////////

    // SRAM Read Request Channel
    input  wire                               rtu_sram_req_valid,
    input  wire [`ADDR_WIDTH-1:0]             rtu_sram_req_raddr,
    output reg                                rtu_sram_req_ready,

    // SRAM Read Response Channel
    output reg                                rtu_sram_resp_valid,
    output reg  [`WLEN-1:0]             rtu_sram_resp_rdata,
    input  wire                               rtu_sram_resp_ready,

    ////////////////////////////////
    //  CORDIC <-> SRAM Interface //
    ////////////////////////////////

    // SRAM Read Request Channel
    input  wire                               cordic_sram_req_valid,
    input  wire [`ADDR_WIDTH-1:0]             cordic_sram_req_raddr,
    output reg                                cordic_sram_req_ready,

    // SRAM Read Response Channel
    output reg                                cordic_sram_resp_valid,
    output reg  [`WLEN-1:0]                   cordic_sram_resp_rdata,
    input  wire                               cordic_sram_resp_ready,

    ////////////////////////////
    //  SRAM Control Signals  //
    ////////////////////////////

    output wire                               wen,
    output wire                               bank_sel, 
    output wire [`ADDR_WIDTH-`BANK_WIDTH-1:0] addr,
    output wire [`DATA_WIDTH-1:0]             din,
    input  wire [`DATA_WIDTH-1:0]             dout
);

endmodule
