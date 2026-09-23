`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module io (
    input  logic        clk,
    input  logic        rst_n,

    input  logic [1:0]  clkdiv_ctl,
    input  logic [7:0]  clkdiv_data,

    ///////////////////////////
    //  I/O -> RTU Interface //
    ///////////////////////////

    render_if.src       render,   // render strobe and image dimensions, to RTU

    //////////////////////
    //  UART Interface  //
    //////////////////////

    input  logic        uart_rx,  // serial data from the host device
    output logic        uart_tx,  // serial data to the host device

    ////////////////////////////////////
    //  Accumulator -> I/O Interface  //
    ////////////////////////////////////

    colour_if.sink      pixel,    // pixel colour stream, from Accumulator

    ///////////////////////////
    // I/O -> SRAM Interface //
    ///////////////////////////

    sram_wr_if.client   sram
);

    /////////////////////////////
    //  UART <-> I/O Interface //
    /////////////////////////////

    stream_if #(.W(8)) rx_bytes ();  // receive byte stream, from UART
    stream_if #(.W(8)) tx_bytes ();  // transmit byte stream, to UART

    logic [7:0] b_reg;
    logic [7:0] c_reg;
    logic clkq;

    uart u_uart (
        .clk   (clk),
        .rst_n (rst_n),
        .rx    (rx_bytes),
        .tx    (tx_bytes),
        .TT_RX (uart_rx),
        .TT_TX (uart_tx)
    );

    clkdiv u_clkdiv (
        .clk(clk),
        .rst_n(rst_n),
        .b(b_reg),
        .c(c_reg),
        .q(clkq)
    );

endmodule
