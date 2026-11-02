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
    output logic [1:0]             material,     // path goes on: 00 matte, 01 mirror, 10 glass. This is FED TO Ray Generator so it knows the type of bounce.
    output logic [35:0]            sample,       // R [35:24], G [23:12], B [11:0], valid with path_end = 1

    // Ray and scene, from RTU registers (must not change from start to done)
    input  logic [47:0]            ray_origin,   // hit point, POS (Q9.7): z [47:32], y [31:16], x [15:0]
    input  logic [47:0]            ray_dir,      // D, DIR (Q2.14), length 1: z [47:32], y [31:16], x [15:0]
    input  logic [23:0]            sky_horizon,  // R [23:16], G [15:8], B [7:0]
    input  logic [23:0]            sky_top,      // same order
    input  logic [23:0]            ground_a,     // checker colours, same order
    input  logic [23:0]            ground_b,

    // SRAM reads (the RTU passes them on to the SRAM Controller)
    output logic [ADDR_WIDTH-1:0]  sram_addr,    // register: address of the word to read
    output logic                   sram_rd,      // 1-cycle pulse: read the word at sram_addr
    input  logic [DATA_WIDTH-1:0]  sram_data,    // SRAM word, shared by all RTU sub-blocks
    input  logic                   sram_valid,   // 1 = sram_data holds the word asked for

    // Macro-ops (the RTU passes them on to the Decode Unit; the macro_if client signals)
    output logic                   req_valid,    // 1 = req_op holds a macro-op
    output logic [101:0]           req_op,       // fmt [101], u [100:53], v [52:5], opcode [4:0]
    input  logic                   req_ready,    // 1 = the Decode Unit takes req_op in this cycle
    input  logic                   resp_valid,   // 1 = resp_result holds the result
    input  logic [3*WLEN-1:0]      resp_result,  // z [47:32], y [31:16], x [15:0]
    output logic                   resp_ready    // 1 = the SC takes resp_result in this cycle
);

localparam SCRATCH_BITS     = 40;
localparam STATE_BITS       = 5;
localparam M_VMUL           = tinytracer_pkg::M_VMUL;
localparam M_VADD           = tinytracer_pkg::M_VADD;
localparam M_VSUB           = tinytracer_pkg::M_VSUB;
localparam M_SCAL_VEC       = tinytracer_pkg::M_SCAL_VEC;

typedef enum logic [STATE_BITS-1:0] {
    STATE_IDLE      ,
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
// -: sram_addr must be held steady until SRAM data is received
// -: we cannot pulse sram_rd=1 on the same posedge where we sample sram_valid=1
// -: we cannot pulse done=1 on the same posedge where we sample start=1
// +: no need to hold req_op steady after req handshake is done (posedge where ready=valid=1)
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
assign dz                 = ray_dir[47] ? 16'b0 : ray_dir[47:32];
assign dz_in              = {3{dz}};
assign sky_ext_in         = { {7{scratch_r[26]}}, scratch_r[26:18], // Red
                              {7{scratch_r[17]}}, scratch_r[17:9],  // Green
                              {7{scratch_r[8]}},  scratch_r[8:0] }; // Blue
assign col_in             = {8'b0, scratch_r[23:16],    8'b0, scratch_r[15:8],    8'b0, scratch_r[7:0]};           
assign str_in             = {2'b0, scratch_r[39:26],    2'b0, scratch_r[39:26],   2'b0, scratch_r[39:26]};

// Macro-op result wires
assign sur_res            = {resp_result[40:33], resp_result[24:17], resp_result[8:1]};
assign sky123w_res        = {resp_result[40:32], resp_result[24:16], resp_result[8:0]};
assign sky4w_res          = {4'b0, resp_result[40:33], 4'b0, resp_result[24:17], 4'b0, resp_result[8:1]};
assign glo1w_res          = {resp_result[40:33], resp_result[24:17], resp_result[8:1]};
assign glo2w_res          = {resp_result[46:35], resp_result[30:19], resp_result[14:3]};

// Miscellaneous next-state wires
assign gnd_col            = (ray_origin[9] ^ ray_origin[25]) ? ground_a : ground_b;

// State transition wires
assign obj1_to_zro        = ~&sram_data[1:0] & last_bounce;
assign obj3_to_glo        = &scratch_r[25:24];

// SRAM read wires
assign sram_addr          = hit_addr + ((state_r == STATE_IDLE || state_r == STATE_OBJ1W) ? 2 :
                                        (state_r == STATE_OBJ2 || state_r == STATE_OBJ2W) ? 1 :
                                                                                            0);
assign sram_rd            = (state_r == STATE_IDLE && &{start, hit, ~hit_ground}) ||
                            (state_r == STATE_OBJ2) ||
                            (state_r == STATE_OBJ3) ;

// Macro-op interface wires
assign req_valid          = (state_r == STATE_SKY1) ||
                            (state_r == STATE_SKY2) ||
                            (state_r == STATE_SKY3) ||
                            (state_r == STATE_SKY4) ||
                            (state_r == STATE_GLO1) ||
                            (state_r == STATE_GLO2) ||
                            (state_r == STATE_SUR)  ;
assign resp_ready         = '1;

// Output wires
assign material           = scratch_r[25:24];

assign done               = (state_r == STATE_ZERO)                                 ||
                            (state_r == STATE_OBJ1W && &{sram_valid, obj1_to_zro})  ||
                            (state_r == STATE_SKY4W && resp_valid)                  ||
                            (state_r == STATE_GLO2W && resp_valid)                  ||
                            (state_r == STATE_SURW  && resp_valid)                  ;

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
  path_end = scratch_r[36];
  case (state_r)
    STATE_GLO2W: path_end = 1'b1;
    // STATE_ZERO:  uses scratch_r value
    // STATE_OBJ1W: uses scratch_r value
    // STATE_SKY4W: uses scratch_r value
    // STATE_SURW:  uses scratch_r value
    default:;
  endcase
end

always_comb begin
  case (state_r)
    //TODO: If there is a global .sv file for opcode params, use those instead of localparams
    STATE_SUR:    req_op = {1'b0, col_p1_in,  att_in,     M_VMUL};
    STATE_SKY1:   req_op = {1'b0, sky_top_in, sky_hor_in, M_VSUB};
    STATE_SKY2:   req_op = {1'b1, dz_in,      sky_ext_in, M_SCAL_VEC};
    STATE_SKY3:   req_op = {1'b0, sky_hor_in, sky_ext_in, M_VADD};
    STATE_SKY4:   req_op = {1'b0, att_p1_in,  sky_ext_in, M_VMUL};
    STATE_GLO1:   req_op = {1'b0, tmp_p1,     col_in    , M_VMUL};
    STATE_GLO2:   req_op = {1'b0, str_in,     col_in    , M_VMUL};
    default:      req_op = 'x;
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
          4'b110?:  state_r <= STATE_OBJ1W;         // Zero sample / Glow sample / Object surface
          4'b1111:  state_r <= STATE_ZERO;          // Zero sample
          4'b1110:  state_r <= STATE_SUR;           // Ground surface
          default:;
        endcase

      STATE_OBJ1W:
        case ({sram_valid, obj1_to_zro})
          2'b11:    state_r <= STATE_IDLE;          // Zero sample
          2'b10:    state_r <= STATE_OBJ2;          // Object surface / Glow sample
          default:;
        endcase

      STATE_OBJ2:                   state_r <= STATE_OBJ2W;
      STATE_OBJ2W:  if (sram_valid) state_r <= STATE_OBJ3;
      STATE_OBJ3:                   state_r <= STATE_OBJ3W;
      STATE_OBJ3W: 
        case ({sram_valid, obj3_to_glo})
          2'b11:    state_r <= STATE_GLO1;          // Glow sample
          2'b10:    state_r <= STATE_SUR;           // Object surface
          default:;
        endcase

      STATE_SUR:    if (req_ready)  state_r <= STATE_SURW;
      STATE_SURW:   if (resp_valid) state_r <= STATE_IDLE;
      STATE_SKY1:   if (req_ready)  state_r <= STATE_SKY1W;
      STATE_SKY1W:  if (resp_valid) state_r <= STATE_SKY2;
      STATE_SKY2:   if (req_ready)  state_r <= STATE_SKY2W;
      STATE_SKY2W:  if (resp_valid) state_r <= STATE_SKY3;
      STATE_SKY3:   if (req_ready)  state_r <= STATE_SKY3W;
      STATE_SKY3W:  if (resp_valid) state_r <= STATE_SKY4;
      STATE_SKY4:   if (req_ready)  state_r <= STATE_SKY4W;
      STATE_SKY4W:  if (resp_valid) state_r <= STATE_IDLE;
      STATE_GLO1:   if (req_ready)  state_r <= STATE_GLO1W;
      STATE_GLO1W:  if (resp_valid) state_r <= STATE_GLO2;
      STATE_GLO2:   if (req_ready)  state_r <= STATE_GLO2W;
      STATE_GLO2W:  if (resp_valid) state_r <= STATE_IDLE;
      STATE_ZERO:                   state_r <= STATE_IDLE;
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
          4'b10??:  scratch_r[36]     <= 1'b1;                // Sky sample
          4'b110?:  scratch_r[36:0]   <= {1'b1, 36'b0};       // Zero sample / Glow sample / Object surface
          4'b1111:  scratch_r[36:0]   <= {1'b1, 36'b0};       // Zero sample
          4'b1110:  scratch_r[25:0]   <= {2'b00, gnd_col};    // Ground surface
          default:;
        endcase

      STATE_OBJ1W:
        case ({sram_valid, obj1_to_zro})
          2'b10:    scratch_r[39:24]  <= sram_data[15:0];     // Read W2 (IMPT: only when -> OBJ2)
          default:;
        endcase

      STATE_OBJ2W:  scratch_r[23:8]   <= sram_data[15:0];     // Read W1
      STATE_OBJ3W:  scratch_r[7:0]    <= sram_data[15:8];     // Read W0
      STATE_SKY1W:  scratch_r[26:0]   <= sky123w_res;
      STATE_SKY2W:  scratch_r[26:0]   <= sky123w_res;
      STATE_SKY3W:  scratch_r[26:0]   <= sky123w_res;        
      STATE_SKY4W:  scratch_r[35:0]   <= sky4w_res;
      STATE_GLO1W:  scratch_r[23:0]   <= glo1w_res;
      STATE_GLO2W:  scratch_r[35:0]   <= glo2w_res;
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
      STATE_IDLE: if (start & new_sample) att_r <= '1;
      STATE_SURW: if (resp_valid)         att_r <= sur_res;
      default:;
    endcase
  end
end

endmodule
