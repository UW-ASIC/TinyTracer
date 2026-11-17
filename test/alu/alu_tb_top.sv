`timescale 1ns/1ps

module alu_tb_top (
    input logic clk,
    input logic rst_n,

    input logic req_valid,
    input logic [15:0] req_op1,
    input logic [15:0] req_op2,
    input logic [2:0] req_opcode,

    output logic req_ready,
    output logic resp_done,
    output logic [15:0] resp_result
);

    fu_if fu();

    // Connect request signals
    assign fu.req_valid = req_valid;
    assign fu.req_op1 = req_op1;
    assign fu.req_op2 = req_op2;
    assign fu.req_opcode = req_opcode;
    assign fu.req_fmt = tinytracer_pkg::fmt_t'(0);

    // Connect response signals
    assign req_ready = fu.req_ready;
    assign resp_done = fu.resp_done;
    assign resp_result = fu.resp_result;

    // Device under test
    alu #(.WLEN(16)) dut (
        .clk(clk),
        .rst_n(rst_n),
        .fu(fu)
    );

endmodule