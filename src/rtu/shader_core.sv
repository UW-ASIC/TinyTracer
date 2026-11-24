// Shader Core: keeps the attenuation and makes the sample colour when the path ends.
module shader_core #(
    parameter ADDR_WIDTH = 9,
    parameter WLEN       = 16,
    parameter DATA_WIDTH = 16
) (
    input  logic                   clk,
    input  logic                   rst_n,        // global reset, active low

    // RTU FSM <-> Shader Core
    input  logic                   new_sample,   // 1-cycle pulse: att = 255
    input  logic                   start,        // 1-cycle pulse: shade one segment
    input  logic                   hit,          // from the IU: 1 = object or ground hit, 0 = sky
    input  logic                   hit_ground,   // from the IU: 1 = the hit is the ground
    input  logic [ADDR_WIDTH-1:0]  hit_addr,     // from the IU: SRAM address of the hit object's w0
    input  logic                   last_bounce,  // 1 when the bounce count is 8: a surface hit gives black
    output logic                   done,         // 1-cycle pulse: the outputs below are valid
    output logic                   path_end,     // 1 = the sample is finished (sky, glow or black)
    output logic [1:0]             material,     // path goes on: 00 matte, 01 mirror, 10 glass.
    output logic [35:0]            sample,       // R [35:24], G [23:12], B [11:0], valid with path_end = 1

    // Ray and scene, from RTU registers (must not change from start to done)
    input  logic                   checker_sel,  // ray origin x[9]^y[9], used for checkerboard drawing
    input  logic [15:0]            dir_z,        // D, DIR (Q2.14), length 1: z [47:32], y [31:16], x [15:0]
    input  logic [23:0]            sky_horizon,  // R [23:16], G [15:8], B [7:0]
    input  logic [23:0]            sky_top,      // same order
    input  logic [23:0]            ground_a,     // checker colours, same order
    input  logic [23:0]            ground_b,

    // SRAM read channel -> SRAM Controller (this block is the client)
    sram_rd_if.client              sram,

    // Macro-ops -> Decode Unit (this block is the client)
    macro_if.client                macro
);

localparam SCRATCH_BITS     = 40;
localparam STATE_BITS       = 5;

typedef enum logic [STATE_BITS-1:0] {
    STATE_IDLE      ,
    STATE_OBJ1      ,
    STATE_OBJ1W     ,
    STATE_OBJ2      ,
    STATE_OBJ2W     ,
    STATE_OBJ3      ,
    STATE_OBJ3W     ,
    STATE_SUR       ,
    STATE_SURW      ,
    STATE_SKY1      ,
    STATE_SKY1W     ,
    STATE_SKY2      ,
    STATE_SKY2W     ,
    STATE_SKY3      ,
    STATE_SKY3W     ,
    STATE_SKY4      ,
    STATE_SKY4W     ,
    STATE_GLO1      ,
    STATE_GLO1W     ,
    STATE_GLO2      ,
    STATE_GLO2W     ,
    STATE_ZERO
} state_t;

// registers
state_t                   state_r;
logic [SCRATCH_BITS-1:0]  scratch_r;
logic [23:0]              att_r;
// wires
logic [23:0]              tmp;
logic [8:0]               tmp_p1_red;
logic [8:0]               tmp_p1_grn;
logic [8:0]               tmp_p1_blu;
logic [3*WLEN-1:0]        tmp_p1;
logic [3*WLEN-1:0]        col_p1_in;
logic [3*WLEN-1:0]        att_p1_in;
logic [3*WLEN-1:0]        att_in;
logic [3*WLEN-1:0]        sky_top_in;
logic [3*WLEN-1:0]        sky_hor_in;
logic [WLEN-1:0]          dz;
logic [3*WLEN-1:0]        dz_in;
logic [3*WLEN-1:0]        sky_ext_in;
logic [3*WLEN-1:0]        col_in;
logic [3*WLEN-1:0]        str_in;
logic [23:0]              sur_res;
logic [26:0]              sky123w_res;
logic [35:0]              sky4w_res;
logic [23:0]              glo1w_res;
logic [35:0]              glo2w_res;
logic [23:0]              gnd_col;
logic                     obj1_to_zro;
logic                     obj3_to_glo;

// --- ASSUMPTIONS ---
// -: SRAM read is not pipelined
// -: sram.req_raddr is held steady in both request and wait states
// -: we cannot pulse sram.req_valid=1 on the same posedge where sram.resp_valid=1 is sampled
// -: we cannot pulse done=1 on the same posedge where start=1 is sampled
// +: no need to hold macro.req_op steady after req handshake is done (posedge where ready=valid=1)
// +: macro-op req handshake must complete (posedge where ready=valid=1) before resp handshake

// Macro-op operand wires
assign tmp                = (state_r == STATE_SUR) ? scratch_r[23:0] : att_r;
assign tmp_p1_red         = {1'b0, tmp[23:16]} + 9'd1;
assign tmp_p1_grn         = {1'b0, tmp[15:8]}  + 9'd1;
assign tmp_p1_blu         = {1'b0, tmp[7:0]}   + 9'd1;
assign tmp_p1             = {7'b0, tmp_p1_red,          7'b0, tmp_p1_grn,         7'b0, tmp_p1_blu};
assign col_p1_in          = tmp_p1;
assign att_p1_in          = tmp_p1;
assign att_in             = {8'b0, att_r[23:16],        8'b0, att_r[15:8],        8'b0, att_r[7:0]};
assign sky_top_in         = {8'b0, sky_top[23:16],      8'b0, sky_top[15:8],      8'b0, sky_top[7:0]};
assign sky_hor_in         = {8'b0, sky_horizon[23:16],  8'b0, sky_horizon[15:8],  8'b0, sky_horizon[7:0]};
assign dz                 = dir_z[15] ? 16'b0 : dir_z;
assign dz_in              = {3{dz}};
assign sky_ext_in         = { {7{scratch_r[26]}}, scratch_r[26:18], // Red
                              {7{scratch_r[17]}}, scratch_r[17:9],  // Green
                              {7{scratch_r[8]}},  scratch_r[8:0] }; // Blue
assign col_in             = {8'b0, scratch_r[23:16],    8'b0, scratch_r[15:8],    8'b0, scratch_r[7:0]};
assign str_in             = {3{2'b0, scratch_r[39:26]}};

// Macro-op result wires
assign sur_res            = {macro.resp_result[40:33], macro.resp_result[24:17], macro.resp_result[8:1]};
assign sky123w_res        = {macro.resp_result[40:32], macro.resp_result[24:16], macro.resp_result[8:0]};
assign sky4w_res          = {4'b0, macro.resp_result[40:33], 4'b0, macro.resp_result[24:17], 4'b0, macro.resp_result[8:1]};
assign glo1w_res          = {macro.resp_result[40:33], macro.resp_result[24:17], macro.resp_result[8:1]};
assign glo2w_res          = {macro.resp_result[46:35], macro.resp_result[30:19], macro.resp_result[14:3]};

// Miscellaneous next-state wires
assign gnd_col            = checker_sel ? ground_b : ground_a;

// State transition wires
assign obj1_to_zro        = ~&sram.resp_rdata[1:0] & last_bounce;
assign obj3_to_glo        = &scratch_r[25:24];

// SRAM read channel wires (client)
assign sram.req_raddr     = hit_addr + ((state_r == STATE_OBJ1 || state_r == STATE_OBJ1W) ? 2 :
                                        (state_r == STATE_OBJ2 || state_r == STATE_OBJ2W) ? 1 :
                                                                                            0);
assign sram.req_valid     = (state_r == STATE_OBJ1) ||
                            (state_r == STATE_OBJ2) ||
                            (state_r == STATE_OBJ3) ;
assign sram.resp_ready    = '1;

// Macro-op interface wires (client)
assign macro.req_valid    = (state_r == STATE_SKY1) ||
                            (state_r == STATE_SKY2) ||
                            (state_r == STATE_SKY3) ||
                            (state_r == STATE_SKY4) ||
                            (state_r == STATE_GLO1) ||
                            (state_r == STATE_GLO2) ||
                            (state_r == STATE_SUR)  ;
assign macro.resp_ready   = '1;

// Output wires
assign done               = (state_r == STATE_ZERO)                                     ||
                            (state_r == STATE_OBJ1W && &{sram.resp_valid, obj1_to_zro}) ||
                            (state_r == STATE_SKY4W && macro.resp_valid)                ||
                            (state_r == STATE_GLO2W && macro.resp_valid)                ||
                            (state_r == STATE_SURW  && macro.resp_valid)                ;
assign material           = scratch_r[25:24];
assign path_end           = scratch_r[36];

// sometimes, done=1 but scratch_r does not have the correct values yet
// to produce correct values, we override sample and path_end with combi logic
// IMPT: only do this if scratch_r cannot be written beforehand
always_comb begin
  sample = scratch_r[35:0];
  case (state_r)
    STATE_SKY4W:  sample = sky4w_res;
    STATE_GLO2W:  sample = glo2w_res;
    // STATE_ZERO:  uses scratch_r value
    // STATE_OBJ1W: uses scratch_r value
    // STATE_SURW:  does not output sample
    default:;
  endcase
end

always_comb begin
  case (state_r)
    STATE_SUR:    macro.req_op = {1'b0, col_p1_in,  att_in,     tinytracer_pkg::M_VMUL};
    STATE_SKY1:   macro.req_op = {1'b0, sky_top_in, sky_hor_in, tinytracer_pkg::M_VSUB};
    STATE_SKY2:   macro.req_op = {1'b1, dz_in,      sky_ext_in, tinytracer_pkg::M_SCAL_VEC};
    STATE_SKY3:   macro.req_op = {1'b0, sky_hor_in, sky_ext_in, tinytracer_pkg::M_VADD};
    STATE_SKY4:   macro.req_op = {1'b0, att_p1_in,  sky_ext_in, tinytracer_pkg::M_VMUL};
    STATE_GLO1:   macro.req_op = {1'b0, tmp_p1,     col_in    , tinytracer_pkg::M_VMUL};
    STATE_GLO2:   macro.req_op = {1'b0, str_in,     col_in    , tinytracer_pkg::M_VMUL};
    default:      macro.req_op = 'x;
  endcase
end

// State register
always_ff @(posedge clk or negedge rst_n) begin
  if (~rst_n) begin
    state_r <= STATE_IDLE;
  end
  else begin
    case (state_r)
      STATE_IDLE:
        casez ({start, hit, hit_ground, last_bounce})
          4'b10??:  state_r <= STATE_SKY1;          // Sky sample
          4'b110?:  state_r <= STATE_OBJ1;          // Zero sample / Glow sample / Object surface
          4'b1111:  state_r <= STATE_ZERO;          // Zero sample
          4'b1110:  state_r <= STATE_SUR;           // Ground surface
          default:;
        endcase

      STATE_OBJ1:   if (sram.req_ready)   state_r <= STATE_OBJ1W;
      STATE_OBJ1W:
        case ({sram.resp_valid, obj1_to_zro})
          2'b11:    state_r <= STATE_IDLE;          // Zero sample
          2'b10:    state_r <= STATE_OBJ2;          // Object surface / Glow sample
          default:;
        endcase

      STATE_OBJ2:   if (sram.req_ready)   state_r <= STATE_OBJ2W;
      STATE_OBJ2W:  if (sram.resp_valid)  state_r <= STATE_OBJ3;
      STATE_OBJ3:   if (sram.req_ready)   state_r <= STATE_OBJ3W;
      STATE_OBJ3W:
        case ({sram.resp_valid, obj3_to_glo})
          2'b11:    state_r <= STATE_GLO1;          // Glow sample
          2'b10:    state_r <= STATE_SUR;           // Object surface
          default:;
        endcase

      STATE_SUR:    if (macro.req_ready)  state_r <= STATE_SURW;
      STATE_SURW:   if (macro.resp_valid) state_r <= STATE_IDLE;
      STATE_SKY1:   if (macro.req_ready)  state_r <= STATE_SKY1W;
      STATE_SKY1W:  if (macro.resp_valid) state_r <= STATE_SKY2;
      STATE_SKY2:   if (macro.req_ready)  state_r <= STATE_SKY2W;
      STATE_SKY2W:  if (macro.resp_valid) state_r <= STATE_SKY3;
      STATE_SKY3:   if (macro.req_ready)  state_r <= STATE_SKY3W;
      STATE_SKY3W:  if (macro.resp_valid) state_r <= STATE_SKY4;
      STATE_SKY4:   if (macro.req_ready)  state_r <= STATE_SKY4W;
      STATE_SKY4W:  if (macro.resp_valid) state_r <= STATE_IDLE;
      STATE_GLO1:   if (macro.req_ready)  state_r <= STATE_GLO1W;
      STATE_GLO1W:  if (macro.resp_valid) state_r <= STATE_GLO2;
      STATE_GLO2:   if (macro.req_ready)  state_r <= STATE_GLO2W;
      STATE_GLO2W:  if (macro.resp_valid) state_r <= STATE_IDLE;
      STATE_ZERO:                         state_r <= STATE_IDLE;
      default:;
    endcase
  end
end

// Scratch register
always_ff @(posedge clk or negedge rst_n) begin
  if (~rst_n) begin
    scratch_r <= '0;
  end
  else begin
    case (state_r)
      STATE_IDLE:
        casez ({start, hit, hit_ground, last_bounce})
          4'b10??:  scratch_r[36]     <= 1'b1;                  // Sky sample
          4'b110?:  scratch_r[36:0]   <= {1'b1, 36'b0};         // Zero sample / Glow sample / Object surface
          4'b1111:  scratch_r[36:0]   <= {1'b1, 36'b0};         // Zero sample
          4'b1110:  scratch_r[25:0]   <= {2'b00, gnd_col};      // Ground surface
          default:;
        endcase

      STATE_OBJ1W:
        case ({sram.resp_valid, obj1_to_zro})
          2'b10:    scratch_r[39:24]  <= sram.resp_rdata[15:0]; // Read W2 (IMPT: only when -> OBJ2)
          default:;
        endcase

      STATE_OBJ2W:  scratch_r[23:8]   <= sram.resp_rdata[15:0]; // Read W1
      STATE_OBJ3W:  scratch_r[7:0]    <= sram.resp_rdata[15:8]; // Read W0
      STATE_SKY1W:  scratch_r[26:0]   <= sky123w_res;
      STATE_SKY2W:  scratch_r[26:0]   <= sky123w_res;
      STATE_SKY3W:  scratch_r[26:0]   <= sky123w_res;
      STATE_SKY4W:  scratch_r[35:0]   <= sky4w_res;
      STATE_GLO1W:  scratch_r[23:0]   <= glo1w_res;
      STATE_GLO2W:  scratch_r[36:0]   <= {1'b1, glo2w_res};
      STATE_SUR:    scratch_r[36]     <= 1'b0;
      default:;
    endcase
  end
end

// Attenuation register
always_ff @(posedge clk or negedge rst_n) begin
  if (~rst_n) begin
    att_r <= '1;
  end
  else begin
    case (state_r)
      STATE_IDLE: if (start & new_sample)    att_r <= '1;
      STATE_SURW: if (macro.resp_valid)      att_r <= sur_res;
      default:;
    endcase
  end
end

endmodule
