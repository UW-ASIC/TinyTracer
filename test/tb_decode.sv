`default_nettype none
`timescale 1ns / 1ps

module tb_decode;

    logic clk;
    logic rst_n;

    // Actual interfaces used by decode
    macro_if macro();
    micro_if micro();

    logic rf_load;
    tinytracer_pkg::vec3_t rf_result;

    // -----------------------------
    // Cocotb-visible macro controls
    // -----------------------------

    logic macro_req_valid;
    logic macro_resp_ready;

    logic [4:0] macro_opcode;
    tinytracer_pkg::fmt_t macro_fmt;

    logic [tinytracer_pkg::WLEN-1:0] macro_u_x;
    logic [tinytracer_pkg::WLEN-1:0] macro_v_x;

    // Cocotb-visible macro outputs
    logic macro_req_ready;
    logic macro_resp_valid;

    // -----------------------------
    // Cocotb-visible micro controls
    // -----------------------------

    logic micro_req_ready;
    logic micro_resp_done;

    // Cocotb-visible micro outputs
    logic micro_req_valid;
    logic micro_req_direct;
    logic [12:0] micro_req_op;
    logic [tinytracer_pkg::WLEN-1:0] micro_req_u1;
    logic [tinytracer_pkg::WLEN-1:0] micro_req_v1;

    // Drive macro interface
    assign macro.req_valid  = macro_req_valid;
    assign macro.resp_ready = macro_resp_ready;

    assign macro_req_ready  = macro.req_ready;
    assign macro_resp_valid = macro.resp_valid;

    // Drive micro interface
    assign micro.req_ready = micro_req_ready;
    assign micro.resp_done = micro_resp_done;

    assign micro_req_valid  = micro.req_valid;
    assign micro_req_direct = micro.req_direct;
    assign micro_req_op     = micro.req_op;
    assign micro_req_u1     = micro.req_u1;
    assign micro_req_v1     = micro.req_v1;

    // Construct macro request
    always @(*) begin
        macro.req_op = '0;

        macro.req_op.op = tinytracer_pkg::macro_op_t'(macro_opcode);
        macro.req_op.fmt = macro_fmt;
        macro.req_op.u.x = macro_u_x;
        macro.req_op.v.x = macro_v_x;
    end

    // Result doesn't matter for most decoder tests yet
    always @(*) begin
        rf_result = '0;
    end

    decode dut (
        .clk       (clk),
        .rst_n     (rst_n),
        .macro     (macro),
        .micro     (micro),
        .rf_load   (rf_load),
        .rf_result (rf_result)
    );

endmodule