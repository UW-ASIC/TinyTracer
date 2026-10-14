`default_nettype wire

// Generic valid/ready stream carrying a W-bit payload (UART bytes).
interface stream_if #(parameter int W = 8);
  logic         valid;
  logic [W-1:0] data;
  logic         ready;
  modport src  (output valid, output data, input  ready);
  modport sink (input  valid, input  data, output ready);
endinterface

// Valid/ready stream carrying one RGB colour, W bits per channel, packed as
// {r, g, b}: W = SAMPLE_DEPTH for samples (RTU -> Accumulator) and
// W = COLOUR_DEPTH for pixels (Accumulator -> I/O).
interface colour_if #(parameter int W = tinytracer_pkg::COLOUR_DEPTH);
  logic           valid;
  logic [3*W-1:0] colour;
  logic           ready;
  modport src  (output valid, output colour, input  ready);
  modport sink (input  valid, input  colour, output ready);
endinterface

// RTU <-> EXU: macro-op request (from the RTU's request register) and vector
// result response (register file R0-R2). The EXU passes the channel through
// to Decode.
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

// RTU sub-block <-> RTU request path. The active sub-block writes fields of
// the shared request register (req_we = {FMT, u3, u2, u1, v3, v2, v1,
// MACROOP}, taking effect at the end of the cycle; macro.req_op shows this
// cycle's writes) and sends it with req_valid. The operand fields take their
// values from req_u and req_v, through the resize pre-shift when req_resize is
// high. The RTU takes every response at once and passes it on with
// resp_valid; resp_flag is resp_result.x[0]. The Ray Generator drives req_u
// and req_v; the Intersection Unit's and Shader Core's operand selects, the
// size shift, and the sign flip are not defined yet. See
// docs/modules/rtu/rtu.md (Handshakes).
interface rtu_req_if;
  logic [7:0]                req_we;
  tinytracer_pkg::fmt_t      req_fmt;
  tinytracer_pkg::vec3_t     req_u;
  tinytracer_pkg::vec3_t     req_v;
  logic                      req_resize;
  tinytracer_pkg::macro_op_t req_op;
  logic                      req_valid;
  logic                      req_ready;
  logic                      resp_valid;
  logic                      resp_flag;
  tinytracer_pkg::vec3_t     resp_result;
  modport client (output req_we, output req_fmt, output req_u, output req_v, output req_resize,
                  output req_op, output req_valid, input  req_ready,
                  input  resp_valid, input  resp_flag, input  resp_result);
  modport server (input  req_we, input  req_fmt, input  req_u, input  req_v, input  req_resize,
                  input  req_op, input  req_valid, output req_ready,
                  output resp_valid, output resp_flag, output resp_result);
endinterface

// Decode <-> FU Control: micro-op request and completion strobe. req_fmt is
// the macro-op's FMT bit. A scalar macro-op's micro-op is issued in the cycle
// the macro-op is accepted, before the register file is loaded, so it sets
// req_direct and carries its operands u1 and v1 in req_u1 and req_v1.
interface micro_if;
  logic                        req_valid;
  tinytracer_pkg::micro_word_t req_op;
  tinytracer_pkg::fmt_t        req_fmt;
  logic                        req_direct;
  logic [tinytracer_pkg::WLEN-1:0]             req_u1;
  logic [tinytracer_pkg::WLEN-1:0]             req_v1;
  logic                        req_ready;
  logic                        resp_done;
  modport client (output req_valid, output req_op, output req_fmt, output req_direct,
                  output req_u1,    output req_v1, input  req_ready, input  resp_done);
  modport server (input  req_valid, input  req_op, input  req_fmt, input  req_direct,
                  input  req_u1,    input  req_v1, output req_ready, output resp_done);
endinterface

// FU Control <-> one functional unit. req_opcode is alu_op_t for the ALU and
// cordic_op_t (in req_opcode[1:0]) for CORDIC; the multiplier ignores it. req_fmt selects the
// multiplier's product shift and the CORDIC square root format; the ALU
// ignores it.
interface fu_if;
  logic                 req_valid;
  logic [tinytracer_pkg::WLEN-1:0]      req_op1;
  logic [tinytracer_pkg::WLEN-1:0]      req_op2;
  logic [2:0]           req_opcode;
  tinytracer_pkg::fmt_t req_fmt;
  logic                 req_ready;
  logic                 resp_done;
  logic [tinytracer_pkg::WLEN-1:0]      resp_result;
  modport client (output req_valid, output req_op1, output req_op2, output req_opcode, output req_fmt,
                  input  req_ready, input  resp_done, input  resp_result);
  modport server (input  req_valid, input  req_op1, input  req_op2, input  req_opcode, input  req_fmt,
                  output req_ready, output resp_done, output resp_result);
endinterface

// Read channel into the SRAM controller (RTU). 512 words, ADDR_WIDTH = 9.
interface sram_rd_if;
  logic                  req_valid;
  logic [tinytracer_pkg::ADDR_WIDTH-1:0] req_raddr;
  logic                  req_ready;
  logic                  resp_valid;
  logic [tinytracer_pkg::DATA_WIDTH-1:0] resp_rdata;
  logic                  resp_ready;
  modport client (output req_valid,  output req_raddr, input  req_ready,
                  input  resp_valid, input  resp_rdata, output resp_ready);
  modport server (input  req_valid,  input  req_raddr, output req_ready,
                  output resp_valid, output resp_rdata, input  resp_ready);
endinterface

// Write channel into the SRAM controller (I/O). 512 words, ADDR_WIDTH = 9.
interface sram_wr_if;
  logic                  req_valid;
  logic                  req_wen;
  logic [tinytracer_pkg::ADDR_WIDTH-1:0] req_waddr;
  logic [tinytracer_pkg::DATA_WIDTH-1:0] req_wdata;
  logic                  req_ready;
  modport client (output req_valid, output req_wen, output req_waddr, output req_wdata, input  req_ready);
  modport server (input  req_valid, input  req_wen, input  req_waddr, input  req_wdata, output req_ready);
endinterface

// I/O -> RTU: one-cycle render strobe plus the image dimensions. img_w and
// img_h are each two RENDER message bytes (low byte first, upper 4 bits of
// the high byte unused) and are held by the I/O unit until the next RENDER
// message. The image is square, with a power-of-2 width of at most 512.
interface render_if;
  logic                 render;
  logic [tinytracer_pkg::DIM_WIDTH-1:0] img_w;
  logic [tinytracer_pkg::DIM_WIDTH-1:0] img_h;
  modport src  (output render, output img_w, output img_h);
  modport sink (input  render, input  img_w, input  img_h);
endinterface
