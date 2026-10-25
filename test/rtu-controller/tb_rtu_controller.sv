`default_nettype wire
`timescale 1ns / 1ps

//Test wrapper for the RTU controller tests (only used for testing)
//The top module can't have interface ports in our simulator, so this wrapper
//makes the interfaces and gives the python test plain wires for render and SRAM
//The macro-op and sample ports aren't used by the controller, so we just tie them off
module tb_rtu_controller(
    input logic clk,
    input logic rst_n,

    //render request
    input logic render,
    input logic [tinytracer_pkg::DIM_WIDTH-1:0] img_w,
    input logic [tinytracer_pkg::DIM_WIDTH-1:0] img_h,

    //SRAM read port (the python test acts as the SRAM)
    output logic sram_req_valid,
    output logic [tinytracer_pkg::ADDR_WIDTH-1:0] sram_req_raddr,
    input logic sram_req_ready,
    input logic sram_resp_valid,
    input logic [tinytracer_pkg::DATA_WIDTH-1:0] sram_resp_rdata,
    output logic sram_resp_ready,

    output logic [tinytracer_pkg::SPP_LOG2_W-1:0] spp_log2
);

  //save waveforms
  initial begin
    $dumpfile("tb_rtu_controller.vcd");
    $dumpvars(0, tb_rtu_controller);
  end

  render_if render_bus();
  sram_rd_if sram_bus();
  macro_if macro_bus();
  colour_if #(.W(tinytracer_pkg::SAMPLE_DEPTH)) sample_bus();

  assign render_bus.render = render;
  assign render_bus.img_w = img_w;
  assign render_bus.img_h = img_h;

  assign sram_req_valid = sram_bus.req_valid;
  assign sram_req_raddr = sram_bus.req_raddr;
  assign sram_resp_ready = sram_bus.resp_ready;
  assign sram_bus.req_ready = sram_req_ready;
  assign sram_bus.resp_valid = sram_resp_valid;
  assign sram_bus.resp_rdata = sram_resp_rdata;

  //tie offs: never take a macro-op, never send a result back, always take samples
  assign macro_bus.req_ready = 1'b0;
  assign macro_bus.resp_valid = 1'b0;
  assign macro_bus.resp_result = '0;
  assign sample_bus.ready = 1'b1;

  rtu u_rtu(
      .clk(clk),
      .rst_n(rst_n),
      .render(render_bus),
      .sram(sram_bus),
      .macro(macro_bus),
      .sample(sample_bus),
      .spp_log2(spp_log2)
  );

endmodule

//---------------------------------------------------------------------------
//Fake sub-blocks, only for this test
//The Makefile uses these instead of the real ray generator, intersection unit
//and shader core, so nothing in the RTL drives done, hit_kind or material
//The python test sets them directly, for example dut.u_rtu.u_ray_generator.done
//The ports are copied from the real modules, so update them if those change
//---------------------------------------------------------------------------

module ray_generator(
    input logic clk,
    input logic rst_n,
    input logic start,
    input logic [1:0] mode,
    output logic done,
    input tinytracer_pkg::vec3_t ray_o,
    input tinytracer_pkg::vec3_t ray_d,
    input tinytracer_pkg::vec3_t ray_n,
    input logic flip,
    input tinytracer_pkg::scratch_t scratch,
    input tinytracer_pkg::vec3_t hdr_f,
    input tinytracer_pkg::vec3_t hdr_r,
    input tinytracer_pkg::vec3_t hdr_u,
    input logic [tinytracer_pkg::WLEN-1:0] cam_z,
    input logic [tinytracer_pkg::PIX_W-1:0] pix_x,
    input logic [tinytracer_pkg::PIX_W-1:0] pix_y,
    input logic [tinytracer_pkg::DIM_WIDTH-1:0] img_w,
    output logic o_we,
    output tinytracer_pkg::vec3_t o_wdata,
    output logic d_we,
    output tinytracer_pkg::vec3_t d_wdata,
    output logic [tinytracer_pkg::SCRATCH_WORDS-1:0] scratch_we,
    output logic [tinytracer_pkg::WLEN-1:0] scratch_wdata,
    rtu_req_if.client req
);
  //done is set by the python test
endmodule

module intersection_unit(
    input logic clk,
    input logic rst_n,
    input logic start,
    input logic [1:0] mode,
    output logic done,
    output tinytracer_pkg::hit_kind_t hit_kind,
    output tinytracer_pkg::mat_type_t material,
    rtu_req_if.client req,
    sram_rd_if.client sram
);
  //done, hit_kind and material are set by the python test
endmodule

module shader_core(
    input logic clk,
    input logic rst_n,
    input logic start,
    input logic [1:0] mode,
    output logic done,
    rtu_req_if.client req,
    colour_if.src sample
);
  //done is set by the python test
endmodule
