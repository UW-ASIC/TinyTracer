`timescale 1ns/1ps

module uart_tb (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       clkq,
    input  logic       TT_RX,
    output wire        TT_TX,

    input  logic       tx_valid,
    input  logic [7:0] tx_data,
    output wire        tx_ready,

    output wire        rx_valid,
    output wire [7:0]  rx_data,
    input  logic       rx_ready
);

    stream_if tx_stream();
    stream_if rx_stream();

    assign tx_stream.valid = tx_valid;
    assign tx_stream.data  = tx_data;
    assign tx_ready        = tx_stream.ready;

    assign rx_valid        = rx_stream.valid;
    assign rx_data         = rx_stream.data;
    assign rx_stream.ready = rx_ready;

    uart dut (
        .clk(clk),
        .rst_n(rst_n),
        .clkq(clkq),
        .TT_RX(TT_RX),
        .TT_TX(TT_TX),
        .tx(tx_stream),
        .rx(rx_stream)
    );

endmodule