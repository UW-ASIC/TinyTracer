`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

// Generic valid/ready stream carrying a W-bit payload (UART bytes).
interface stream_if #(parameter int W = 8);
  logic         valid;
  logic [W-1:0] data;
  logic         ready;
  modport src  (output valid, output data, input  ready);
  modport sink (input  valid, input  data, output ready);
endinterface

// Valid/ready stream carrying one RGB colour (samples, pixels).
interface colour_if;
  logic                  valid;
  tinytracer_pkg::rgb_t  colour;
  logic                  ready;
  modport src  (output valid, output colour, input  ready);
  modport sink (input  valid, input  colour, output ready);
endinterface

// RTU <-> Decode: macro-op request and vector result response.
interface macro_if;
  logic                        req_valid;
  tinytracer_pkg::macro_word_t req_op;
  logic                        req_ready;
  logic                        resp_valid;
  tinytracer_pkg::vec3_t       resp_result;
  logic                        resp_ready;
  modport client (output req_valid,  output req_op,       input  req_ready,
                  input  resp_valid, input  resp_result,  output resp_ready);
  modport server (input  req_valid,  input  req_op,       output req_ready,
                  output resp_valid, output resp_result,  input  resp_ready);
endinterface

// Decode <-> FU Control: micro-op request and completion strobe.
interface micro_if;
  logic                        req_valid;
  tinytracer_pkg::micro_word_t req_op;
  logic                        req_ready;
  logic                        resp_done;
  modport client (output req_valid, output req_op, input  req_ready, input  resp_done);
  modport server (input  req_valid, input  req_op, output req_ready, output resp_done);
endinterface

// FU Control <-> one functional unit. req_opcode is alu_op_t for the ALU and
// cordic_op_t for CORDIC; the multiplier and RNG ignore it (and the RNG op2).
interface fu_if;
  logic            req_valid;
  logic [WLEN-1:0] req_op1;
  logic [WLEN-1:0] req_op2;
  logic [2:0]      req_opcode;
  logic            req_ready;
  logic            resp_done;
  logic [WLEN-1:0] resp_result;
  modport client (output req_valid, output req_op1, output req_op2, output req_opcode, input  req_ready,
                  input  resp_done, input  resp_result);
  modport server (input  req_valid, input  req_op1, input  req_op2, input  req_opcode, output req_ready,
                  output resp_done, output resp_result);
endinterface

// Read channel into the SRAM controller (RTU).
interface sram_rd_if;
  logic                  req_valid;
  logic [ADDR_WIDTH-1:0] req_raddr;
  logic                  req_ready;
  logic                  resp_valid;
  logic [DATA_WIDTH-1:0] resp_rdata;
  logic                  resp_ready;
  modport client (output req_valid,  output req_raddr, input  req_ready,
                  input  resp_valid, input  resp_rdata, output resp_ready);
  modport server (input  req_valid,  input  req_raddr, output req_ready,
                  output resp_valid, output resp_rdata, input  resp_ready);
endinterface

// Write channel into the SRAM controller (I/O).
interface sram_wr_if;
  logic                  req_valid;
  logic                  req_wen;
  logic [ADDR_WIDTH-1:0] req_waddr;
  logic [DATA_WIDTH-1:0] req_wdata;
  logic                  req_ready;
  modport client (output req_valid, output req_wen, output req_waddr, output req_wdata, input  req_ready);
  modport server (input  req_valid, input  req_wen, input  req_waddr, input  req_wdata, output req_ready);
endinterface

// I/O -> RTU: one-cycle render strobe plus the image dimensions. img_w and
// img_h are each two RENDER message bytes (low byte first, upper 4 bits of
// the high byte unused) and are held by the I/O unit until the next RENDER
// message.
interface render_if;
  logic                 render;
  logic [DIM_WIDTH-1:0] img_w;
  logic [DIM_WIDTH-1:0] img_h;
  modport src  (output render, output img_w, output img_h);
  modport sink (input  render, input  img_w, input  img_h);
endinterface
