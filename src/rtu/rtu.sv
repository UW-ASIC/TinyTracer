`default_nettype wire

module rtu (
    input  logic        clk,
    input  logic        rst_n,

    // I/O <-> RTU Interface
    render_if.sink      render,   // render strobe and image dimensions, from I/O

    // RTU <-> SRAM Interface
    sram_rd_if.client   sram,

    // RTU <-> EXU Interface
    macro_if.client     macro,

    // RTU <-> Accumulator Interface
    colour_if.src       sample,   // sample colour stream (W = SAMPLE_DEPTH), to Accumulator
    output logic [tinytracer_pkg::SPP_LOG2_W-1:0] spp_log2  // log2(samples per pixel), from the header
);

  // Controller <-> sub-block handshakes: start and done are one-cycle pulses,
  // mode is valid with start (see docs/modules/rtu/rtu.md, Handshakes)
  logic                      rg_start;
  logic [1:0]                rg_mode;
  logic                      rg_done;
  logic                      iu_start;
  logic                      iu_done;
  logic                      sh_start;
  logic                      sh_done;

  // Block that owns the request path and the SRAM read port
  tinytracer_pkg::rtu_blk_t  active;

  // Header and ray state registers that the Ray Generator reads (see
  // docs/modules/rtu/rtu.md, Ray State Registers)
  tinytracer_pkg::vec3_t     ray_o;
  tinytracer_pkg::vec3_t     ray_d;
  tinytracer_pkg::vec3_t     ray_n;
  logic                      flip;
  tinytracer_pkg::scratch_t  scratch;
  tinytracer_pkg::vec3_t     hdr_f;
  tinytracer_pkg::vec3_t     hdr_r;
  tinytracer_pkg::vec3_t     hdr_u;
  logic [tinytracer_pkg::WLEN-1:0]      cam_z;
  logic [tinytracer_pkg::PIX_W-1:0]     pix_x;
  logic [tinytracer_pkg::PIX_W-1:0]     pix_y;

  // Ray Generator writes to O, D, and the scratch registers
  logic                      rg_o_we;
  tinytracer_pkg::vec3_t     rg_o_wdata;
  logic                      rg_d_we;
  tinytracer_pkg::vec3_t     rg_d_wdata;
  logic [tinytracer_pkg::SCRATCH_WORDS-1:0] rg_scratch_we;
  logic [tinytracer_pkg::WLEN-1:0]          rg_scratch_wdata;

  // Sub-block <-> request path
  rtu_req_if rg_req ();
  macro_if iu_macro ();
  macro_if sh_macro ();

  // IU Regs
  sram_rd_if iu_sram ();
  logic                      iu_hit;         // object or ground hit, 0 = sky
  logic                      iu_hit_ground;  // the hit is the ground
  logic                      iu_hit_flip;    // sphere: the ray started inside
  tinytracer_pkg::vec3_t     iu_hit_point;   // hit point, POS
  tinytracer_pkg::vec3_t     iu_n;           // surface normal, DIR, faces the ray
  logic                      iu_checker_bit; // ground: hit point x[9] ^ y[9]

  // Shader Core Regs
  sram_rd_if sh_sram ();
  logic                      sh_new_sample;  // with start: first segment of a sample, attenuation = 255
  logic                      sh_last_bounce; // bounce count is at the limit
  logic                      sh_path_end;    // with done: the sample is finished
  logic [1:0]                sh_material;    // path goes on: material of the surface, held until the next start
  logic [3*tinytracer_pkg::SAMPLE_DEPTH-1:0] sh_sample;  // {r, g, b}, held after done

  tinytracer_pkg::rgb_t sky_hor, sky_top, gnd_a, gnd_b;
  logic [tinytracer_pkg::ADDR_WIDTH-1:0] hit_addr;
  logic [4:0]                bv_num;
  logic [1:0] rg_mode_curr, rg_mode_prev;

  ray_generator u_ray_generator (
      .clk           (clk),
      .rst_n         (rst_n),
      .start         (rg_start),
      .mode          (rg_mode_curr),
      .done          (rg_done),
      .ray_o         (ray_o),
      .ray_d         (ray_d),
      .ray_n         (ray_n),
      .flip          (flip),
      .scratch       (scratch),
      .hdr_f         (hdr_f),
      .hdr_r         (hdr_r),
      .hdr_u         (hdr_u),
      .cam_z         (cam_z),
      .pix_x         (pix_x),
      .pix_y         (pix_y),
      .img_w         (render.img_w),
      .o_we          (rg_o_we),
      .o_wdata       (rg_o_wdata),
      .d_we          (rg_d_we),
      .d_wdata       (rg_d_wdata),
      .scratch_we    (rg_scratch_we),
      .scratch_wdata (rg_scratch_wdata),
      .req           (rg_req)
  );

  intersection_unit u_intersection_unit (
    .clk          (clk),
    .rst_n        (rst_n),
    .start        (iu_start),
    .done         (iu_done),
    .hit          (iu_hit),
    .hit_ground   (iu_hit_ground),
    .hit_addr     (hit_addr),
    .hit_flip     (iu_hit_flip),
    .hit_point    (iu_hit_point),
    .n            (iu_n),
    .checker_bit  (iu_checker_bit),
    .ray_origin   (ray_o),
    .ray_dir      (ray_d),
    .bv_count     (bv_num),

    .sram         (iu_sram),
    .macro        (iu_macro),

    // debug ports
    .state_q      (),
    .state_d      (),
    .sram_state_q (),
    .sram_state_d (),
    .dec_state_q  (),
    .dec_state_d  (),
    .calc_stage_q (),
    .calc_stage_d (),
    .dbg_obj_addr (),
    .dbg_obj_cnt  ()
  );

  // The Shader Core sends samples straight out of the RTU's sample port
  shader_core u_shader_core (
    .clk         (clk),
    .rst_n       (rst_n),
    .new_sample  (sh_new_sample),
    .start       (sh_start),
    .hit         (iu_hit),
    .hit_ground  (iu_hit_ground),
    .hit_addr    (hit_addr),
    .last_bounce (sh_last_bounce),
    .done        (sh_done),
    .path_end    (sh_path_end),
    .material    (sh_material),
    .sample      (sh_sample),
    .checker_sel (iu_checker_bit),
    .dir_z       (ray_d.z),
    .sky_horizon (sky_hor),
    .sky_top     (sky_top),
    .ground_a    (gnd_a),
    .ground_b    (gnd_b),

    .sram        (sh_sram),
    .macro       (sh_macro)
  );

  // actual rtl part
  // IDLE: idle state, waiting for render signal
  // HDR: loads header signals
  // RG_CAM: raygen camera ray
  // IU_SEARCH: intersection unit search
  // SH_SHADE: shader core
  // SAMPLE_WAIT: completed sample (waiting for acccumulator)
  // RG_MAT: raygen bounce ray

  typedef enum logic [3:0] {
    IDLE, HDR, RG_CAM, IU_SEARCH, SH_SHADE, SAMPLE_WAIT, RG_MAT
  } ctrl_state;
  ctrl_state state, next_state;

  // header registers
  logic [4:0] sample_cnt;
  logic [3:0] bounce_cnt;
  logic [4:0] max_samples; // max of spp_log2 is 32, so 5 bits is needed
  logic last_col, last_row;
  logic sample_start, sample_done, frame_done, final_sample;

  logic[4:0] hdr_idx, hdr_idx_next;
  logic hdr_pending, hdr_sram_valid, hdr_finish, hdr_req_valid;
  logic rg_active, iu_active, sc_active, ctrl_active;

  assign max_samples = (1 << spp_log2) - 1; // number of samples to count to per pixel
  assign last_col = (pix_x == (render.img_w - 1)); // pixel on right border
  assign last_row = (pix_y == (render.img_h - 1)); // pixel on bottom
  assign sh_last_bounce = (bounce_cnt == tinytracer_pkg::MAX_BOUNCES);
  assign final_sample = (sample_cnt == max_samples);

  assign sample.valid = (state == SAMPLE_WAIT);
  assign sample.colour = sh_sample;

  assign rg_mode_curr = rg_start ? rg_mode: rg_mode_prev;

  // state FSM
  always_comb begin
    // raygen
    rg_start = 0;
    rg_mode = 0;

    // intersection unit
    iu_start = 0;

    // shader core
    sh_start = 0;

    // misc
    sample_start = 0;
    sample_done = 0;
    frame_done = 0;

    next_state = state;
    case (state)
      IDLE: begin
        if (render.render) begin
          next_state = HDR;
        end
      end

      HDR: begin
        if (hdr_finish) begin
          sample_start = 1;
        end
      end

      RG_CAM: begin
        if (rg_done) begin
          iu_start = 1;
          next_state = IU_SEARCH;
        end
      end

      IU_SEARCH: begin
        if (iu_done) begin
          sh_start = 1;
          next_state = SH_SHADE;
        end
      end

      SH_SHADE: begin // shader core
        if (sh_done) begin
          if (sh_path_end) begin // last bounce logic handled here
            next_state = SAMPLE_WAIT; // finish sample, pass to accumulator
          end else begin
            rg_start = 1;
            rg_mode = sh_material + 1; // feed next material to rg
            next_state = RG_MAT;
          end
        end
      end

      // ! Check accumulator timing to see if this can be merged into SH_SHADE
      SAMPLE_WAIT: begin
        if (sample.ready) begin // wait for accumulator
          sample_done = 1;
          if (last_col && last_row && final_sample) begin
            frame_done = 1;
            next_state = IDLE;
          end else begin
            sample_start = 1; // start next sample
          end
        end
      end

      RG_MAT: begin // bounce based on material
        if (rg_done) begin
          next_state = IU_SEARCH;
          iu_start = 1;
        end
      end

      default: next_state = IDLE;
    endcase

    // sample reset logic
    if (sample_start) begin
      rg_mode = 0;
      rg_start = 1;
      next_state = RG_CAM;
    end
  end

  // controller logic
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      active <= tinytracer_pkg::BLK_CTRL;
      state <= IDLE;
      pix_x <= 0;
      pix_y <= 0;
      sample_cnt <= 0;
      bounce_cnt <= 0;
      rg_mode_prev <= 0;
      sh_new_sample <= 0;
    end else begin
      state <= next_state;

      // sample initialization logic
      if (rg_start) begin
        rg_mode_prev <= rg_mode;
      end

      if (sample_start) begin
        bounce_cnt <= 0;
        sh_new_sample <= 1;
      end else begin
        if (state == RG_MAT && rg_done) begin
          bounce_cnt <= bounce_cnt + 1;
        end

        if (sh_start) begin
          sh_new_sample <= 0;
        end
      end

      // counter resetting
      if (state == IDLE && render.render) begin
        pix_x <= 0;
        pix_y <= 0;
        sample_cnt <= 0;
      end

      // active block logic
      if (frame_done) begin
        active <= tinytracer_pkg::BLK_CTRL;
      end else if (rg_start) begin
        active <= tinytracer_pkg::BLK_RAY_GEN;
      end else if (iu_start) begin
        active <= tinytracer_pkg::BLK_ISECT;
      end else if (sh_start) begin
        active <= tinytracer_pkg::BLK_SHADER;
      end

      // advance sample counter logic
      if (sample_done) begin
        if (!final_sample) begin
          sample_cnt <= sample_cnt + 1;
        end else begin
          sample_cnt <= 0;
          // move to next pixel
          if (!last_col) begin
            pix_x <= pix_x + 1;
          end else begin
            pix_x <= 0;
            if (!last_row) begin
              pix_y <= pix_y + 1;
            end
          end
        end
      end
    end
  end 

  // header logic
  /*

  logic: each header word is 16 bits. i guess colours are split between multiple words (check how)
  BV_NUM and SPP_LOG2 are combined into one (8 bits total)

  Registers:
  F, R, U -> 9 x 16 bits -> w0 - w8
  sky colours (horizon and top) -> 2 x 24 bits -> w9 - w11
  ground colours (A and B) -> 2  x 24 bits -> w12 - w14
  BV_NUM, SPP_LOG2 -> 5, 3 bits -> w15 
  CAM_Z -> 16 bits -> w16

  Headers take 2 cycles per word to read -> store curr header word and also get header word ready logic set up

  */

  assign hdr_sram_valid = (state == HDR) && hdr_pending && sram.resp_valid;
  assign hdr_finish = hdr_sram_valid && (hdr_idx == (tinytracer_pkg::HDR_WORDS - 1));

  assign rg_active = (active == tinytracer_pkg::BLK_RAY_GEN);
  assign iu_active = (active == tinytracer_pkg::BLK_ISECT);
  assign sc_active = (active == tinytracer_pkg::BLK_SHADER);
  assign ctrl_active = (active == tinytracer_pkg::BLK_CTRL);

  assign hdr_idx_next = hdr_idx + 1;

  // logic for reading next hdr_idx
  always_comb begin
    hdr_req_valid = 0;
    if (state == HDR) begin
      if (!hdr_pending) begin
        hdr_req_valid = 1;
      end else if (sram.resp_valid && (hdr_idx != (tinytracer_pkg::HDR_WORDS - 1))) begin
        // if valid, move to next hdr word
        hdr_req_valid = 1;
      end
    end
  end

  // header index counter logic
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      hdr_idx  <= 0;
      hdr_pending <= 0;
    end else if (state == IDLE) begin // on sample finishes. kept separate to distinguish between this and reset
      hdr_idx  <= 0;
      hdr_pending <= 0;
    end else if (state == HDR) begin
      if (!hdr_pending) begin
        if (sram.req_ready) hdr_pending <= 1;
      end else if (sram.resp_valid) begin
        if (hdr_idx != (tinytracer_pkg::HDR_WORDS - 1)) begin
          hdr_idx  <= hdr_idx_next;
          hdr_pending <= sram.req_ready; // next request accepted in this cycle, or retry
        end else begin
          hdr_pending <= 0; // resets on next cycle
        end
      end
    end
  end

  // header read logic
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      hdr_f <= 0;
      hdr_r <= 0;
      hdr_u <= 0;
      sky_hor <= 0;
      sky_top <= 0;
      gnd_a <= 0;
      gnd_b <= 0;
      bv_num <= 0;
      spp_log2 <= 0;
      cam_z <= 0;
    end else if (hdr_sram_valid) begin
      case (hdr_idx)
        5'd0: hdr_f.x <= sram.resp_rdata;
        5'd1: hdr_f.y <= sram.resp_rdata;
        5'd2: hdr_f.z <= sram.resp_rdata;
        5'd3: hdr_r.x <= sram.resp_rdata;
        5'd4: hdr_r.y <= sram.resp_rdata;
        5'd5: hdr_r.z <= sram.resp_rdata;
        5'd6: hdr_u.x <= sram.resp_rdata;
        5'd7: hdr_u.y <= sram.resp_rdata;
        5'd8: hdr_u.z <= sram.resp_rdata;
        5'd9: begin
          sky_hor.r <= sram.resp_rdata[15:8];
          sky_hor.g <= sram.resp_rdata[7:0];
        end
        5'd10: begin
          sky_hor.b <= sram.resp_rdata[15:8];
          sky_top.r <= sram.resp_rdata[7:0];
        end
        5'd11: begin
          sky_top.g <= sram.resp_rdata[15:8];
          sky_top.b <= sram.resp_rdata[7:0];
        end
        5'd12: begin
          gnd_a.r <= sram.resp_rdata[15:8];
          gnd_a.g <= sram.resp_rdata[7:0];
        end
        5'd13: begin
          gnd_a.b <= sram.resp_rdata[15:8];
          gnd_b.r <= sram.resp_rdata[7:0];
        end
        5'd14: begin
          gnd_b.g <= sram.resp_rdata[15:8];
          gnd_b.b <= sram.resp_rdata[7:0];
        end
        5'd15: begin
          bv_num <= sram.resp_rdata[7:3];
          spp_log2 <= sram.resp_rdata[2:0];
        end
        5'd16: cam_z <= sram.resp_rdata;
        default: ;
      endcase
    end
  end

  // ray state regs
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      ray_o <= 0;
      ray_d <= 0;
      ray_n <= 0;
      flip <= 0;
      scratch <= 0;

    end else begin
      // update raygen regs
      if (rg_o_we && rg_active) ray_o <= rg_o_wdata;
      if (rg_d_we && rg_active) ray_d <= rg_d_wdata;
      
      // update iu regs
      if (state == IU_SEARCH && iu_done && iu_hit) begin
        ray_o <= iu_hit_point;
        ray_n <= iu_n;
        flip <= iu_hit_flip;
      end
      // scratch regs updates
      for (int i = 0; i < tinytracer_pkg::SCRATCH_WORDS; i++) begin
        if (rg_active && rg_scratch_we[i]) begin
          scratch[i] <= rg_scratch_wdata;
        end
      end
    end
  end

  // SRAM read/req logic
  assign sram.resp_ready = 1; // keeps resp_ready high

  assign iu_sram.req_ready  = sram.req_ready && iu_active;
  assign iu_sram.resp_valid = sram.resp_valid && iu_active;
  assign iu_sram.resp_rdata = sram.resp_rdata;

  assign sh_sram.req_ready  = sram.req_ready && sc_active;
  assign sh_sram.resp_valid = sram.resp_valid && sc_active;
  assign sh_sram.resp_rdata = sram.resp_rdata;

  // The shader core pulses sram_rd for one cycle and holds sram_addr until the word is back
  logic iu_rd_pending;
  logic [tinytracer_pkg::ADDR_WIDTH-1:0] iu_rd_addr;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      iu_rd_pending <= 0;
      iu_rd_addr <= 0;
    end else if (sram.req_ready) begin
      iu_rd_pending <= 0;
    end else if (iu_active && iu_sram.req_valid) begin
      iu_rd_pending <= 1;
      iu_rd_addr <= iu_sram.req_raddr;
    end
  end

  // sram mux
  always_comb begin
    sram.req_valid = 0;
    sram.req_raddr = 0;

    if (ctrl_active) begin
      sram.req_valid = hdr_req_valid;
      sram.req_raddr = hdr_pending ? hdr_idx_next : hdr_idx;
    end else if (iu_active) begin
      sram.req_valid = iu_sram.req_valid || iu_rd_pending;
      sram.req_raddr = iu_rd_pending ? iu_rd_addr : iu_sram.req_raddr;
    end else if (sc_active) begin
      sram.req_valid = sh_sram.req_valid;
      sram.req_raddr = sh_sram.req_raddr;
    end
  end

  // request path
  tinytracer_pkg::fmt_t req_fmt;
  tinytracer_pkg::vec3_t req_u, req_v;
  tinytracer_pkg::macro_op_t req_op;
  logic req_resize, req_valid;

  always_comb begin
    // ! Note: can optimize some of these default mux values by setting some of these to default to ray_gen
    req_fmt = tinytracer_pkg::FMT_POS;
    req_u = 0;
    req_v = 0;
    req_resize = 0;
    req_valid = 0;
    req_op = tinytracer_pkg::M_ADD;
    case (active)
      tinytracer_pkg::BLK_RAY_GEN: begin
        req_fmt    = rg_req.req_fmt;
        req_u      = rg_req.req_u;
        req_v      = rg_req.req_v;
        req_resize = rg_req.req_resize;
        req_op     = rg_req.req_op;
        req_valid  = rg_req.req_valid;
      end

      // resize is not used in iu or sc
      tinytracer_pkg::BLK_ISECT: begin
        req_fmt    = iu_macro.req_op.fmt;
        req_u      = iu_macro.req_op.u;
        req_v      = iu_macro.req_op.v;
        req_op     = iu_macro.req_op.op;
        req_valid  = iu_macro.req_valid;
      end

      tinytracer_pkg::BLK_SHADER: begin
        req_fmt    = sh_macro.req_op.fmt;
        req_u      = sh_macro.req_op.u;
        req_v      = sh_macro.req_op.v;
        req_op     = sh_macro.req_op.op;
        req_valid  = sh_macro.req_valid;
      end

      default: ;
    endcase
  end

  // resize logic
  logic [3:0]  u_lead;  // index of the highest bit
  tinytracer_pkg::vec3_t req_u_shifted;

  // checks (with sign) whether one of the bits is 1. the highest one is assigned the index
  always_comb begin
    u_lead = 0;
    for (int i = 0; i < 15; i++) begin
      if ((req_u.x[i] ^ req_u.x[15]) | (req_u.y[i] ^ req_u.y[15]) | (req_u.z[i] ^ req_u.z[15])) begin
        u_lead = i;
      end
    end
  end

  // logic behind bit 13: for DIR, bit 13 is weighted 0.5. Since the max val should be 0.5-1 in DIR, bit 14 should be 0
  // this essentially shifts the x, y, z values such that the leading bit is 13
  always_comb begin
    req_u_shifted = req_u;
    if (req_resize) begin
      if (u_lead == 14) begin // top bit is 14
        req_u_shifted.x = $signed(req_u.x) >>> 1;
        req_u_shifted.y = $signed(req_u.y) >>> 1;
        req_u_shifted.z = $signed(req_u.z) >>> 1;
      end else begin         // shift left by 0 to 13
        req_u_shifted.x = req_u.x <<< (13 - u_lead);
        req_u_shifted.y = req_u.y <<< (13 - u_lead);
        req_u_shifted.z = req_u.z <<< (13 - u_lead);
      end
    end
  end

  // Macro Ops
  assign macro.req_valid = req_valid;
  assign macro.req_op = {req_fmt, req_u_shifted, req_v, req_op};

  assign macro.resp_ready = 1;

  assign rg_req.req_ready = macro.req_ready;
  assign rg_req.resp_valid = macro.resp_valid && rg_active;
  assign rg_req.resp_flag = macro.resp_result.x[0];
  assign rg_req.resp_result = macro.resp_result;

  assign iu_macro.req_ready = macro.req_ready;
  assign iu_macro.resp_valid = macro.resp_valid && iu_active;
  assign iu_macro.resp_result = macro.resp_result;

  assign sh_macro.req_ready = macro.req_ready;
  assign sh_macro.resp_valid = macro.resp_valid && sc_active;
  assign sh_macro.resp_result = macro.resp_result;

endmodule
