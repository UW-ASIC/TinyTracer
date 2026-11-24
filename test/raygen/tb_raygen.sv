`timescale 1ns / 1ps

// Standalone wrapper: exposes ray_generator's interface signals as normal
// top-level signals so cocotb can access them as dut.req_op, dut.req_u, etc.
module tb_raygen (
    input  logic clk,
    input  logic rst_n,
    input  logic start,
    input  logic [1:0] mode,
    output logic done,

    input  tinytracer_pkg::vec3_t ray_o,
    input  tinytracer_pkg::vec3_t ray_d,
    input  tinytracer_pkg::vec3_t ray_n,
    input  logic flip,
    input  tinytracer_pkg::scratch_t scratch,
    input  tinytracer_pkg::vec3_t hdr_f,
    input  tinytracer_pkg::vec3_t hdr_r,
    input  tinytracer_pkg::vec3_t hdr_u,
    input  logic [tinytracer_pkg::WLEN-1:0] cam_z,
    input  logic [tinytracer_pkg::PIX_W-1:0] pix_x,
    input  logic [tinytracer_pkg::PIX_W-1:0] pix_y,
    input  logic [tinytracer_pkg::DIM_WIDTH-1:0] img_w,

    output logic o_we,
    output tinytracer_pkg::vec3_t o_wdata,
    output logic d_we,
    output tinytracer_pkg::vec3_t d_wdata,
    output logic [tinytracer_pkg::SCRATCH_WORDS-1:0] scratch_we,
    output logic [tinytracer_pkg::WLEN-1:0] scratch_wdata,

    output logic [7:0] req_we,
    output tinytracer_pkg::fmt_t req_fmt,
    output tinytracer_pkg::vec3_t req_u,
    output tinytracer_pkg::vec3_t req_v,
    output logic req_resize,
    output tinytracer_pkg::macro_op_t req_op,
    output logic req_valid,
    input logic req_ready,
    input logic resp_valid,
    input logic resp_flag,
    input tinytracer_pkg::vec3_t resp_result
);
    rtu_req_if req();

    // DUT -> cocotb
    assign req_we     = req.req_we;
    assign req_fmt    = req.req_fmt;
    assign req_u      = req.req_u;
    assign req_v      = req.req_v;
    assign req_resize = req.req_resize;
    assign req_op     = req.req_op;
    assign req_valid  = req.req_valid;

    // cocotb -> DUT
    assign req.req_ready   = req_ready;
    assign req.resp_valid  = resp_valid;
    assign req.resp_flag   = resp_flag;
    assign req.resp_result = resp_result;

    ray_generator dut (
        .clk, .rst_n, .start, .mode, .done,
        .ray_o, .ray_d, .ray_n, .flip, .scratch,
        .hdr_f, .hdr_r, .hdr_u, .cam_z, .pix_x, .pix_y, .img_w,
        .o_we, .o_wdata, .d_we, .d_wdata,
        .scratch_we, .scratch_wdata,
        .req(req)
    );

    initial begin
        $dumpfile("raygen.vcd");
        $dumpvars(0, tb_raygen);
    end
endmodule