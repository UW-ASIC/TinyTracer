`timescale 1ns/1ps
`default_nettype none

module tb_multiplier (
    input logic clk,
    input logic rst_n,
    input logic [15:0] multiplicand,
    input logic [15:0] multiplier_in,
    output wire [31:0] product
);

    // Eva's multiplier has this interface port, but does not use it yet.
    // Keep it connected and hold its request inputs idle.
    fu_if fu();

    assign fu.req_valid = 1'b0;
    assign fu.req_op1 = '0;
    assign fu.req_op2 = '0;
    assign fu.req_opcode = '0;
    assign fu.req_fmt = tinytracer_pkg::FMT_POS;

    multiplier dut (
        .clk(clk),
        .rst_n(rst_n),
        .multiplicand(multiplicand),
        .multiplier_in(multiplier_in),
        .product(product),
        .fu(fu)
    );

endmodule

`default_nettype wire