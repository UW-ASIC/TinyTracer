`default_nettype none
`timescale 1ns / 1ps

module tb_uart (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       clkq,
    input  logic       TT_RX,
    output logic       TT_TX,
    output logic       rx_valid,
    output logic [7:0] rx_data,
    input  logic       rx_ready,
    input  logic       tx_valid,
    input  logic [7:0] tx_data,
    output logic       tx_ready
);

    stream_if #(.W(8)) rx_if ();
    stream_if #(.W(8)) tx_if ();

    assign rx_valid    = rx_if.valid;
    assign rx_data     = rx_if.data;
    assign rx_if.ready = rx_ready;

    assign tx_if.valid = tx_valid;
    assign tx_if.data  = tx_data;
    assign tx_ready    = tx_if.ready;

    uart dut (
        .clk   (clk),
        .rst_n (rst_n),
        .clkq  (clkq),
        .rx    (rx_if),
        .tx    (tx_if),
        .TT_RX (TT_RX),
        .TT_TX (TT_TX)
    );

    initial begin
        $dumpfile("tb_uart.vcd");
        $dumpvars(0, tb_uart);
    end

endmodule
