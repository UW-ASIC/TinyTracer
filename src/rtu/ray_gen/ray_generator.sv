`default_nettype wire

// Makes the camera ray of each sample and the new ray after each bounce. The
// RTU owns the shared registers: the Ray Generator reads them on input ports,
// builds its macro-op operands from them, and writes O, D, and scratch words
// through its write ports (see docs/modules/rtu/ray_gen/ray_generator.md).
//
// Every ray is a fixed sequence of macro-ops on the RTU request path. The FSM
// has one state per macro-op, and each state has two phases:
//   send (waiting = 0): write the request fields and raise req_valid until
//                       req_ready is high (the macro-op is sent that cycle)
//   wait (waiting = 1): hold until resp_valid, then store the result (scratch,
//                       O or D) and move to the next state
//
// Sequences (state prefix)
//   camera  P_    aR, F+aR, bU, F+aR+bU, resize           O = (0, 0, CAM_Z)
//   matte   M_    phi, z^2, 1-z^2, rho, rho cos, phi-pi/2, rho sin, n+r,
//                 resize (skipped when n+r = 0)
//   mirror  R_    D.n, 2(D.n), 2(D.n)n, D-2(D.n)n
//   glass   G_    D.n, cos, k, Schlick share, compare, then reflect (joins the
//                 mirror states) or refract
//   bounce  PUSH_ O = hit point + 0.031 n  (- 0.031 n for a refracted ray)
//
// Notes
//   - Glass reflects with D - 2(D.n)n, the same value as D + 2cos(t)n because
//     cos(t) = -(D.n), so it reuses the mirror states.
//   - k < 0 is read from the sign bit of k, so it takes no compare macro-op,
//     and total internal reflection skips the Schlick share. Glass takes 67
//     (reflect) or 167 (refract) cycles before the push-off.
//   - Every macro-op uses FMT_DIR: all products here are DIR x DIR -> DIR.
//     The push-off scalar 4 times a DIR normal gives 4 POS steps along n.
module ray_generator (
    input  logic                            clk,
    input  logic                            rst_n,

    // Controller <-> Ray Generator Signals (start, done: one-cycle pulses)
    input  logic                            start,           // Start signal from the Controller; mode valid with it
    input  logic [1:0]                      mode,            // 0: camera ray, 1: matte or ground, 2: mirror, 3: glass
    output logic                            done,            // New ray written this cycle; O and D hold it from the next

    // RTU registers, read only (the RTU owns and writes them)
    input  tinytracer_pkg::vec3_t           ray_o,           // O: ray origin, or the hit point after a surface hit
    input  tinytracer_pkg::vec3_t           ray_d,           // D: ray direction
    input  tinytracer_pkg::vec3_t           ray_n,           // n: surface normal, faces the incoming ray
    input  logic                            flip,            // Kept flip bit (glass): the ray started inside
    input  tinytracer_pkg::scratch_t        scratch,         // Scratch registers
    input  tinytracer_pkg::vec3_t           hdr_f,           // Camera vectors F, R, U (header registers)
    input  tinytracer_pkg::vec3_t           hdr_r,
    input  tinytracer_pkg::vec3_t           hdr_u,
    input  logic [tinytracer_pkg::WLEN-1:0] cam_z,           // CAM_Z: camera height (header register)
    input  logic [tinytracer_pkg::PIX_W-1:0] pix_x,          // Pixel being rendered (Controller counters)
    input  logic [tinytracer_pkg::PIX_W-1:0] pix_y,
    input  logic [tinytracer_pkg::DIM_WIDTH-1:0] img_w,      // Image width (render_if): where the jitter bits start

    // RTU register writes, taking effect at the end of the cycle; raised only while active
    output logic                            o_we,            // Write o_wdata into O
    output tinytracer_pkg::vec3_t           o_wdata,
    output logic                            d_we,            // Write d_wdata into D
    output tinytracer_pkg::vec3_t           d_wdata,
    output logic [tinytracer_pkg::SCRATCH_WORDS-1:0] scratch_we, // Write scratch_wdata into each word whose bit is high
    output logic [tinytracer_pkg::WLEN-1:0] scratch_wdata,

    // Ray Generator <-> RTU Request Path Interface (operand values on req_u, req_v)
    rtu_req_if.client                       req
);

  // LFSR state. The Ray Generator places its bits into operands by wiring and
  // pulses rng_req in each cycle it writes a request field from them.
  logic [tinytracer_pkg::WLEN-1:0] rand_num;
  logic                            rng_req;  // advance the LFSR by 16 steps at the end of the cycle

  rng u_rng (
      .clk      (clk),
      .rst_n    (rst_n),
      .req      (rng_req),
      .rand_num (rand_num)
  );

  //---------------------------- Constants -------------------------------------

  localparam int WLEN  = tinytracer_pkg::WLEN;
  localparam int PIX_W = tinytracer_pkg::PIX_W;

  localparam logic [1:0] MODE_CAMERA = 2'd0;
  localparam logic [1:0] MODE_MATTE  = 2'd1;  // also the ground
  localparam logic [1:0] MODE_MIRROR = 2'd2;
  localparam logic [1:0] MODE_GLASS  = 2'd3;

  // DIR numbers (Q2.14, 1.0 = 16384)
  localparam logic [WLEN-1:0] DIR_ONE   = 16'd16384;  // 1.0
  localparam logic [WLEN-1:0] K_PI_2    = 16'd25736;  // pi/2 = 1.5708
  localparam logic [WLEN-1:0] K_ETA_IN  = 16'd10923;  // 1/1.5 = 0.6667, entering the glass
  localparam logic [WLEN-1:0] K_ETA_OUT = 16'd24576;  // 1.5, leaving the glass
  localparam logic [WLEN-1:0] K_R0      = 16'd655;    // 0.04, Schlick R0 for index 1.5
  localparam logic [WLEN-1:0] K_1MR0    = 16'd15729;  // 0.96 = 1 - R0

  // Push-off scalar: (4 x n) >>> 14 is 4 POS steps along a DIR normal n
  localparam logic [WLEN-1:0] K_PUSH     = 16'd4;
  localparam logic [WLEN-1:0] K_PUSH_NEG = 16'hFFFC;  // -4

  // Scratch words. Matte and glass never run together, so they share words.
  localparam logic [2:0] SC_PHI  = 3'd0;  // matte  : phi = w pi/2
  localparam logic [2:0] SC_Z    = 3'd1;  // matte  : z
  localparam logic [2:0] SC_RHO  = 3'd2;  // matte  : rho = sqrt(1 - z^2)
  localparam logic [2:0] SC_RCOS = 3'd3;  // matte  : rho cos(phi)
  localparam logic [2:0] SC_DOT  = 3'd0;  // mirror, glass : D . n
  localparam logic [2:0] SC_COS  = 3'd1;  // glass  : cos(theta) = -(D . n)
  localparam logic [2:0] SC_K    = 3'd2;  // glass  : k = 1 - eta^2 (1 - cos^2)
  localparam logic [2:0] SC_X    = 3'd3;  // glass  : 1 - cos(theta), the Schlick base
  localparam logic [2:0] SC_SQK  = 3'd4;  // glass  : sqrt(k)
  localparam int         SC_USED = 5;     // words 0 .. SC_USED-1 are used

  //---------------------------- States ----------------------------------------

  typedef enum logic [5:0] {
    S_IDLE,
    // Camera ray
    S_P_AR,      // a R
    S_P_FAR,     // F + aR                        -> D (parked for S_P_SUM)
    S_P_BU,      // b U
    S_P_SUM,     // (F + aR) + bU
    S_P_NORM,    // resize                        -> D, O = (0, 0, CAM_Z), done
    // Matte and ground
    S_M_PHI,     // phi = w pi/2                  -> scratch
    S_M_ZSQ,     // z z   (z -> scratch as the request is sent)
    S_M_1MZ,     // 1 - z^2
    S_M_RHO,     // rho = sqrt(1 - z^2)           -> scratch
    S_M_RCOS,    // rho cos(phi)                  -> scratch
    S_M_PHM,     // phi - pi/2
    S_M_RSIN,    // rho sin(phi) = rho cos(phi - pi/2)
    S_M_NR,      // n + r   (if 0: D = n and skip the resize)
    S_M_NORM,    // resize                        -> D
    // Mirror (glass reflections join at S_R_2DN)
    S_R_DOT,     // D . n                         -> scratch
    S_R_2DN,     // 2 (D . n)
    S_R_SCL,     // 2 (D . n) n
    S_R_SUB,     // D - 2 (D . n) n               -> D
    // Glass
    S_G_COS,     // cos = 0 - D . n               -> scratch
    S_G_C2,      // cos^2
    S_G_S2,      // 1 - cos^2
    S_G_ES2,     // eta (1 - cos^2)
    S_G_E2S2,    // eta^2 (1 - cos^2)
    S_G_K,       // k = 1 - eta^2 (1 - cos^2)     -> scratch; k < 0: reflect
    S_G_X,       // x = 1 - cos                   -> scratch
    S_G_X2,      // x^2
    S_G_X4,      // x^4
    S_G_X5,      // x^5
    S_G_SCH,     // 0.96 x^5
    S_G_R,       // R = 0.04 + 0.96 x^5
    S_G_CMP,     // rand - R: < 0 reflect, else refract
    S_G_ED,      // eta D                         -> D (parked for S_G_SUM)
    S_G_SQK,     // sqrt(k)                       -> scratch
    S_G_EC,      // eta cos
    S_G_COEF,    // eta cos - sqrt(k)
    S_G_CN,      // (eta cos - sqrt(k)) n
    S_G_SUM,     // eta D + (eta cos - sqrt(k)) n
    S_G_NORM,    // resize                        -> D
    // Push-off, every bounce
    S_PUSH_SCL,  // +-4 POS steps along n
    S_PUSH_ADD   // hit point + that              -> O, done
  } state_e;

  state_e     state;
  logic       waiting;  // macro-op sent, waiting for resp_valid
  logic [1:0] mode_q;   // mode, registered with start
  logic       refract;  // glass ray refracts: push the origin into the glass

  logic busy, issue, fire, resp_ok;
  assign busy    = (state != S_IDLE);
  assign issue   = busy && !waiting;                  // send phase
  assign fire    = issue && req.req_ready;            // macro-op sent this cycle
  assign resp_ok = busy && waiting && req.resp_valid; // its result is here

  tinytracer_pkg::vec3_t res;  // last macro-op result
  logic [WLEN-1:0]       rx;   // the same, as a scalar
  assign res = req.resp_result;
  assign rx  = res.x;

  //---------------------------- Random bits -----------------------------------

  // 8 random bits as a DIR number in [0, 0.996]: w, and the Schlick compare
  logic [WLEN-1:0] r_unit;
  assign r_unit = {2'b00, rand_num[7:0], 6'b0};

  // 8 random bits as a DIR number in [-0.992, 0.992]: z. -128 reads as -127.
  logic [7:0]      z_bits;
  logic [WLEN-1:0] r_signed;
  assign z_bits   = (rand_num[7:0] == 8'h80) ? 8'h81 : rand_num[7:0];
  assign r_signed = {z_bits[7], z_bits, 7'b0};

  // Random signs of r, applied by XOR (~v is -v - 1: a 1-LSB error)
  logic [WLEN-1:0] r_x, r_y;
  assign r_x = scratch[SC_RCOS] ^ {WLEN{rand_num[0]}};
  assign r_y = rx               ^ {WLEN{rand_num[1]}};

  // Glass: entering the sphere eta = 1/1.5, leaving it eta = 1.5
  logic [WLEN-1:0] eta;
  assign eta = flip ? K_ETA_OUT : K_ETA_IN;

  //---------------------------- Camera jitter a, b ----------------------------
  // a = (x - W/2) / (W/2) and b = (W/2 - 1 - y) / (W/2) as DIR numbers, made by
  // placing bits. With L = log2(W):
  //   x - W/2      is x with bit L-1 inverted       (L-bit two's complement)
  //   W/2 - 1 - y  is y with bits L-2..0 inverted
  // Both are sign-extended and moved up 15 - L bits, so one pixel is
  // 2^(15-L) DIR steps, and the 15 - L bits below are random (jitter).
  // For W = 512: a = {~x8, ~x8, x[7:0], rand[5:0]}, b = {y8, y8, ~y[7:0], rand[5:0]}

  localparam int LOG_W = $clog2(WLEN);  // wide enough for L and 15 - L

  logic [LOG_W-1:0] img_log2;  // L, from the one set bit of img_w (1 .. PIX_W)
  logic [WLEN-1:0]  px, py;    // pixel counters, zero-extended
  logic [WLEN-1:0]  xc, yc;    // x - W/2 and W/2 - 1 - y, sign-extended
  logic [LOG_W-1:0] jit_bits;  // 15 - L
  logic [WLEN-1:0]  jit_mask;  // the low 15 - L bits
  logic [WLEN-1:0]  jit_a, jit_b;

  always_comb begin
    img_log2 = LOG_W'(1);
    for (int i = 1; i <= PIX_W; i++)
      if (img_w[i]) img_log2 = LOG_W'(i);
  end

  always_comb begin
    px = {{(WLEN-PIX_W){1'b0}}, pix_x};
    py = {{(WLEN-PIX_W){1'b0}}, pix_y};
    for (int i = 0; i < WLEN; i++) begin
      if (i + 1 < img_log2) begin
        xc[i] =  px[i];
        yc[i] = ~py[i];
      end else begin
        xc[i] = ~px[img_log2 - 1];
        yc[i] =  py[img_log2 - 1];
      end
    end
  end

  assign jit_bits = LOG_W'(WLEN - 1) - img_log2;
  assign jit_mask = ~({WLEN{1'b1}} << jit_bits);
  assign jit_a    = (xc << jit_bits) | (rand_num & jit_mask);
  assign jit_b    = (yc << jit_bits) | (rand_num & jit_mask);

  //---------------------------- Request (send phase) --------------------------
  // What each state sends. Scalars travel in u1 and v1 (field x).

  tinytracer_pkg::macro_op_t op;
  tinytracer_pkg::vec3_t     opu, opv;
  logic                      resize;    // resize pre-shift on u, before M_NORM
  logic                      use_rand;  // the request is built from rand_num
  logic                      iss_z_we;  // save z to scratch as the request is sent

  always_comb begin
    op       = tinytracer_pkg::M_ADD;
    opu      = '0;
    opv      = '0;
    resize   = 1'b0;
    use_rand = 1'b0;
    iss_z_we = 1'b0;

    case (state)
      // Camera ray
      S_P_AR:   begin op = tinytracer_pkg::M_SCAL_VEC; opu.x = jit_a; opv = hdr_r; use_rand = 1'b1; end
      S_P_FAR:  begin op = tinytracer_pkg::M_VADD;     opu = hdr_f;   opv = res;                    end
      S_P_BU:   begin op = tinytracer_pkg::M_SCAL_VEC; opu.x = jit_b; opv = hdr_u; use_rand = 1'b1; end
      S_P_SUM:  begin op = tinytracer_pkg::M_VADD;     opu = ray_d;   opv = res;                    end
      S_P_NORM: begin op = tinytracer_pkg::M_NORM;     opu = res;     resize = 1'b1;                end

      // Matte and ground
      S_M_PHI:  begin op = tinytracer_pkg::M_MUL;  opu.x = r_unit;   opv.x = K_PI_2;   use_rand = 1'b1; end
      S_M_ZSQ:  begin op = tinytracer_pkg::M_MUL;  opu.x = r_signed; opv.x = r_signed; use_rand = 1'b1;
                      iss_z_we = 1'b1;                                                                  end
      S_M_1MZ:  begin op = tinytracer_pkg::M_SUB;  opu.x = DIR_ONE;         opv.x = rx;                end
      S_M_RHO:  begin op = tinytracer_pkg::M_SQRT; opu.x = rx;                                         end
      S_M_RCOS: begin op = tinytracer_pkg::M_COS;  opu.x = rx;              opv.x = scratch[SC_PHI];   end
      S_M_PHM:  begin op = tinytracer_pkg::M_SUB;  opu.x = scratch[SC_PHI]; opv.x = K_PI_2;            end
      S_M_RSIN: begin op = tinytracer_pkg::M_COS;  opu.x = scratch[SC_RHO]; opv.x = rx;                end
      S_M_NR:   begin  // n + r, r = (+-rho cos, +-rho sin, z)
        op       = tinytracer_pkg::M_VADD;
        opu      = ray_n;
        opv.x    = r_x;
        opv.y    = r_y;
        opv.z    = scratch[SC_Z];
        use_rand = 1'b1;
      end
      S_M_NORM: begin op = tinytracer_pkg::M_NORM; opu = res; resize = 1'b1; end

      // Mirror
      S_R_DOT:  begin op = tinytracer_pkg::M_DOT;      opu = ray_d;             opv = ray_n;             end
      S_R_2DN:  begin op = tinytracer_pkg::M_ADD;      opu.x = scratch[SC_DOT]; opv.x = scratch[SC_DOT]; end
      S_R_SCL:  begin op = tinytracer_pkg::M_SCAL_VEC; opu.x = rx;              opv = ray_n;             end
      S_R_SUB:  begin op = tinytracer_pkg::M_VSUB;     opu = ray_d;             opv = res;               end

      // Glass
      S_G_COS:  begin op = tinytracer_pkg::M_SUB;      opu.x = '0;              opv.x = rx;              end
      S_G_C2:   begin op = tinytracer_pkg::M_MUL;      opu.x = rx;              opv.x = rx;              end
      S_G_S2:   begin op = tinytracer_pkg::M_SUB;      opu.x = DIR_ONE;         opv.x = rx;              end
      S_G_ES2:  begin op = tinytracer_pkg::M_MUL;      opu.x = eta;             opv.x = rx;              end
      S_G_E2S2: begin op = tinytracer_pkg::M_MUL;      opu.x = eta;             opv.x = rx;              end
      S_G_K:    begin op = tinytracer_pkg::M_SUB;      opu.x = DIR_ONE;         opv.x = rx;              end
      S_G_X:    begin op = tinytracer_pkg::M_SUB;      opu.x = DIR_ONE;         opv.x = scratch[SC_COS]; end
      S_G_X2:   begin op = tinytracer_pkg::M_MUL;      opu.x = rx;              opv.x = rx;              end
      S_G_X4:   begin op = tinytracer_pkg::M_MUL;      opu.x = rx;              opv.x = rx;              end
      S_G_X5:   begin op = tinytracer_pkg::M_MUL;      opu.x = rx;              opv.x = scratch[SC_X];   end
      S_G_SCH:  begin op = tinytracer_pkg::M_MUL;      opu.x = rx;              opv.x = K_1MR0;          end
      S_G_R:    begin op = tinytracer_pkg::M_ADD;      opu.x = rx;              opv.x = K_R0;            end
      S_G_CMP:  begin op = tinytracer_pkg::M_SUB;      opu.x = r_unit;          opv.x = rx; use_rand = 1'b1; end
      S_G_ED:   begin op = tinytracer_pkg::M_SCAL_VEC; opu.x = eta;             opv = ray_d;             end
      S_G_SQK:  begin op = tinytracer_pkg::M_SQRT;     opu.x = scratch[SC_K];                            end
      S_G_EC:   begin op = tinytracer_pkg::M_MUL;      opu.x = eta;             opv.x = scratch[SC_COS]; end
      S_G_COEF: begin op = tinytracer_pkg::M_SUB;      opu.x = rx;              opv.x = scratch[SC_SQK]; end
      S_G_CN:   begin op = tinytracer_pkg::M_SCAL_VEC; opu.x = rx;              opv = ray_n;             end
      S_G_SUM:  begin op = tinytracer_pkg::M_VADD;     opu = ray_d;             opv = res;               end
      S_G_NORM: begin op = tinytracer_pkg::M_NORM;     opu = res;               resize = 1'b1;           end

      // Push-off, every bounce
      S_PUSH_SCL: begin
        op    = tinytracer_pkg::M_SCAL_VEC;
        opu.x = refract ? K_PUSH_NEG : K_PUSH;
        opv   = ray_n;
      end
      S_PUSH_ADD: begin op = tinytracer_pkg::M_VADD; opu = ray_o; opv = res; end

      default: ;  // S_IDLE
    endcase
  end

  // Operand fields each macro-op reads: {u3, u2, u1} and {v3, v2, v1}
  logic [2:0] u_fields, v_fields;

  always_comb begin
    case (op)
      tinytracer_pkg::M_DOT, tinytracer_pkg::M_VADD,
      tinytracer_pkg::M_VSUB, tinytracer_pkg::M_NORM:     u_fields = 3'b111;
      default:                                            u_fields = 3'b001;
    endcase
    case (op)
      tinytracer_pkg::M_SQRT, tinytracer_pkg::M_NORM:     v_fields = 3'b000;
      tinytracer_pkg::M_DOT, tinytracer_pkg::M_VADD,
      tinytracer_pkg::M_VSUB, tinytracer_pkg::M_SCAL_VEC: v_fields = 3'b111;
      default:                                            v_fields = 3'b001;
    endcase
  end

  // Request register writes: {FMT, u3, u2, u1, v3, v2, v1, MACROOP}. They stay
  // the same while req_ready is low: rand_num only moves when the op is sent.
  assign req.req_we     = issue ? {1'b1, u_fields, v_fields, 1'b1} : 8'b0;
  assign req.req_fmt    = tinytracer_pkg::FMT_DIR;
  assign req.req_op     = op;
  assign req.req_u      = opu;
  assign req.req_v      = opv;
  assign req.req_resize = issue && resize;
  assign req.req_valid  = issue;
  assign rng_req        = fire && use_rand;

  //---------------------------- Response (wait phase) -------------------------
  // Where each state's result goes, and the next state.

  state_e                nxt;
  logic                  rsp_sc_we;    // write rx into scratch word rsp_sc_idx
  logic [2:0]            rsp_sc_idx;
  logic                  rsp_d_we;
  tinytracer_pkg::vec3_t rsp_d;
  logic                  rsp_o_we;
  tinytracer_pkg::vec3_t rsp_o;
  logic                  set_refract;
  logic                  finish;

  always_comb begin
    nxt         = state;
    rsp_sc_we   = 1'b0;
    rsp_sc_idx  = '0;
    rsp_d_we    = 1'b0;
    rsp_d       = res;
    rsp_o_we    = 1'b0;
    rsp_o       = res;
    set_refract = 1'b0;
    finish      = 1'b0;

    case (state)
      // Camera ray
      S_P_AR:   nxt = S_P_FAR;
      S_P_FAR:  begin nxt = S_P_BU; rsp_d_we = 1'b1; end
      S_P_BU:   nxt = S_P_SUM;
      S_P_SUM:  nxt = S_P_NORM;
      S_P_NORM: begin
        nxt      = S_IDLE;
        rsp_d_we = 1'b1;
        rsp_o_we = 1'b1;
        rsp_o    = '0;
        rsp_o.z  = cam_z;
        finish   = 1'b1;
      end

      // Matte and ground
      S_M_PHI:  begin nxt = S_M_ZSQ;  rsp_sc_we = 1'b1; rsp_sc_idx = SC_PHI;  end
      S_M_ZSQ:  nxt = S_M_1MZ;
      S_M_1MZ:  nxt = S_M_RHO;
      S_M_RHO:  begin nxt = S_M_RCOS; rsp_sc_we = 1'b1; rsp_sc_idx = SC_RHO;  end
      S_M_RCOS: begin nxt = S_M_PHM;  rsp_sc_we = 1'b1; rsp_sc_idx = SC_RCOS; end
      S_M_PHM:  nxt = S_M_RSIN;
      S_M_RSIN: nxt = S_M_NR;
      S_M_NR: begin
        if (res == '0) begin  // the resize would find no leading 1: D = n
          nxt      = S_PUSH_SCL;
          rsp_d_we = 1'b1;
          rsp_d    = ray_n;
        end else begin
          nxt      = S_M_NORM;
        end
      end
      S_M_NORM: begin nxt = S_PUSH_SCL; rsp_d_we = 1'b1; end

      // Mirror
      S_R_DOT: begin
        nxt        = (mode_q == MODE_GLASS) ? S_G_COS : S_R_2DN;
        rsp_sc_we  = 1'b1;
        rsp_sc_idx = SC_DOT;
      end
      S_R_2DN:  nxt = S_R_SCL;
      S_R_SCL:  nxt = S_R_SUB;
      S_R_SUB:  begin nxt = S_PUSH_SCL; rsp_d_we = 1'b1; end

      // Glass
      S_G_COS:  begin nxt = S_G_C2; rsp_sc_we = 1'b1; rsp_sc_idx = SC_COS; end
      S_G_C2:   nxt = S_G_S2;
      S_G_S2:   nxt = S_G_ES2;
      S_G_ES2:  nxt = S_G_E2S2;
      S_G_E2S2: nxt = S_G_K;
      S_G_K: begin
        nxt        = rx[WLEN-1] ? S_R_2DN : S_G_X;  // k < 0: total internal reflection
        rsp_sc_we  = 1'b1;
        rsp_sc_idx = SC_K;
      end
      S_G_X:    begin nxt = S_G_X2; rsp_sc_we = 1'b1; rsp_sc_idx = SC_X; end
      S_G_X2:   nxt = S_G_X4;
      S_G_X4:   nxt = S_G_X5;
      S_G_X5:   nxt = S_G_SCH;
      S_G_SCH:  nxt = S_G_R;
      S_G_R:    nxt = S_G_CMP;
      S_G_CMP: begin
        if (rx[WLEN-1]) begin  // rand < R: reflect
          nxt         = S_R_2DN;
        end else begin
          nxt         = S_G_ED;
          set_refract = 1'b1;
        end
      end
      S_G_ED:   begin nxt = S_G_SQK; rsp_d_we = 1'b1; end
      S_G_SQK:  begin nxt = S_G_EC;  rsp_sc_we = 1'b1; rsp_sc_idx = SC_SQK; end
      S_G_EC:   nxt = S_G_COEF;
      S_G_COEF: nxt = S_G_CN;
      S_G_CN:   nxt = S_G_SUM;
      S_G_SUM:  nxt = S_G_NORM;
      S_G_NORM: begin nxt = S_PUSH_SCL; rsp_d_we = 1'b1; end

      // Push-off, every bounce
      S_PUSH_SCL: nxt = S_PUSH_ADD;
      S_PUSH_ADD: begin nxt = S_IDLE; rsp_o_we = 1'b1; finish = 1'b1; end

      default: nxt = S_IDLE;
    endcase
  end

  //---------------------------- Outputs ---------------------------------------

  assign o_we    = resp_ok && rsp_o_we;
  assign o_wdata = rsp_o;
  assign d_we    = resp_ok && rsp_d_we;
  assign d_wdata = rsp_d;
  assign done    = resp_ok && finish;

  // One scratch word per cycle: z as its request is sent, or a stored result
  always_comb begin
    scratch_we    = '0;
    scratch_wdata = '0;
    if (fire && iss_z_we) begin
      scratch_we[SC_Z] = 1'b1;
      scratch_wdata    = r_signed;
    end else if (resp_ok && rsp_sc_we) begin
      scratch_we[rsp_sc_idx] = 1'b1;
      scratch_wdata          = rx;
    end
  end

  //---------------------------- FSM -------------------------------------------

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state   <= S_IDLE;
      waiting <= 1'b0;
      mode_q  <= MODE_CAMERA;
      refract <= 1'b0;
    end else if (state == S_IDLE) begin
      if (start) begin  // registers mode; start is ignored while busy
        case (mode)
          MODE_CAMERA:             state <= S_P_AR;
          MODE_MATTE:              state <= S_M_PHI;
          MODE_MIRROR, MODE_GLASS: state <= S_R_DOT;  // both start with D . n
          default:                 state <= S_IDLE;
        endcase
        mode_q  <= mode;
        refract <= 1'b0;
      end
    end else if (fire) begin
      waiting <= 1'b1;
    end else if (resp_ok) begin
      state   <= nxt;
      waiting <= 1'b0;
      if (set_refract) refract <= 1'b1;
    end
  end

  // Read but unused: the compare flag, image widths above 2^PIX_W, spare scratch
  logic unused;
  assign unused = ^{req.resp_flag, img_w[tinytracer_pkg::DIM_WIDTH-1:PIX_W+1], img_w[0],
                    scratch[tinytracer_pkg::SCRATCH_WORDS-1:SC_USED]};

endmodule
