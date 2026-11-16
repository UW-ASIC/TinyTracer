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
  logic [1:0]                iu_mode;
  logic                      iu_done;
  tinytracer_pkg::hit_kind_t iu_hit_kind;
  tinytracer_pkg::mat_type_t iu_material;
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
  logic [tinytracer_pkg::DIM_WIDTH-1:0] img_w;

  assign img_w = render.img_w;

  // Ray Generator writes to O, D, and the scratch registers
  logic                      rg_o_we;
  tinytracer_pkg::vec3_t     rg_o_wdata;
  logic                      rg_d_we;
  tinytracer_pkg::vec3_t     rg_d_wdata;
  logic [tinytracer_pkg::SCRATCH_WORDS-1:0] rg_scratch_we;
  logic [tinytracer_pkg::WLEN-1:0]          rg_scratch_wdata;

  // Sub-block <-> request path
  rtu_req_if rg_req ();
  rtu_req_if iu_req ();

  // Intersection Unit SRAM reads, connected to sram while it is active
  sram_rd_if iu_sram ();

  // Shader Core Regs
  logic                      sh_new_sample;  // with start: first segment of a sample, attenuation = 255
  logic                      sh_hit;         // object or ground hit
  logic                      sh_hit_ground;
  logic                      sh_last_bounce; // bounce count is at the limit
  logic                      sh_path_end;    // with done: the sample is finished
  logic [1:0]                sh_material;    // path goes on: material of the surface, held until the next start
  logic [3*tinytracer_pkg::SAMPLE_DEPTH-1:0] sh_sample;  // {r, g, b}, held after done
  logic                      sh_checker_sel;
  tinytracer_pkg::rgb_t sky_hor, sky_top, gnd_a, gnd_b;
  logic [tinytracer_pkg::ADDR_WIDTH-1:0] sh_sram_addr;
  logic                      sh_sram_rd;
  logic                      sh_sram_valid;
  logic                      sh_req_valid;
  logic [tinytracer_pkg::MACRO_W-1:0]    sh_req_op;
  logic                      sh_resp_valid;
  logic                      sh_resp_ready;

  ray_generator u_ray_generator (
      .clk           (clk),
      .rst_n         (rst_n),
      .start         (rg_start),
      .mode          (rg_mode),
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
      .img_w         (img_w),
      .o_we          (rg_o_we),
      .o_wdata       (rg_o_wdata),
      .d_we          (rg_d_we),
      .d_wdata       (rg_d_wdata),
      .scratch_we    (rg_scratch_we),
      .scratch_wdata (rg_scratch_wdata),
      .req           (rg_req)
  );

  intersection_unit u_intersection_unit (
      .clk      (clk),
      .rst_n    (rst_n),
      .start    (iu_start),
      .mode     (iu_mode),
      .done     (iu_done),
      .hit_kind (iu_hit_kind),
      .material (iu_material),
      .req      (iu_req),
      .sram     (iu_sram)
  );

  // The Shader Core sends samples straight out of the RTU's sample port
  shader_core #(
    .ADDR_WIDTH (tinytracer_pkg::ADDR_WIDTH),
    .WLEN       (tinytracer_pkg::WLEN),
    .DATA_WIDTH (tinytracer_pkg::DATA_WIDTH)
  ) u_shader_core (
    .clk         (clk),
    .rst_n       (rst_n),
    .new_sample  (sh_new_sample),
    .start       (sh_start),
    .hit         (sh_hit),
    .hit_ground  (sh_hit_ground),
    .hit_addr    (hit_addr),
    .last_bounce (sh_last_bounce),
    .done        (sh_done),
    .path_end    (sh_path_end),
    .material    (sh_material),
    .sample      (sh_sample),
    .checker_sel (sh_checker_sel),
    .dir_z       (ray_d.z),
    .sky_horizon (sky_hor),
    .sky_top     (sky_top),
    .ground_a    (gnd_a),
    .ground_b    (gnd_b),
    .sram_addr   (sh_sram_addr),
    .sram_rd     (sh_sram_rd),
    .sram_data   (sram.resp_rdata),
    .sram_valid  (sh_sram_valid),
    .req_valid   (sh_req_valid),
    .req_op      (sh_req_op),
    .req_ready   (macro.req_ready),
    .resp_valid  (sh_resp_valid),
    .resp_result (macro.resp_result),
    .resp_ready  (sh_resp_ready)
  );

  // actual rtl part
  // IDLE: idle state, waiting for render signal
  // HDR: loads header signals
  // RG_CAM: raygen camera ray
  // IU_SEARCH: intersection unit search (mode 0)
  // IU_HIT_GND: intersection unit hit point (mode 2) for a ground hit
  // SH_SHADE: shader core
  // SAMPLE_WAIT: completed sample (waiting for acccumulator)
  // IU_HIT: intersection unit hit point and normal (mode 2) for an object hit
  // RG_MAT: raygen bounce ray

  typedef enum logic [3:0] {
    IDLE, HDR, RG_CAM, IU_SEARCH, IU_HIT_GND, SH_SHADE, SAMPLE_WAIT, IU_HIT, RG_MAT
  } ctrl_state;
  ctrl_state state, next_state;

  // header registers
  logic [4:0] sample_cnt;

  logic [3:0] bounce_cnt;
  logic [7:0] atten;
  logic [4:0] max_samples; // max of spp_log2 is 32, so 5 bits is needed
  logic last_col, last_row;
  logic sample_start, sample_done, frame_done, final_sample;

  tinytracer_pkg::hit_kind_t hit_kind_now, hit_kind_prev; // hit_kind_prev stores the IU pulsed hit kind

  assign max_samples = (1 << spp_log2) - 1; // number of samples to count to per pixel
  assign last_col = (pix_x == (img_w - 1)); // pixel on right border
  assign last_row = (pix_y == (img_h - 1)); // pixel on bottom
  assign sh_last_bounce = (bounce_cnt == tinytracer_pkg::MAX_BOUNCES);
  assign final_sample = (sample_cnt == max_samples);

  assign hit_kind_now = (state == IU_SEARCH) ? iu_hit_kind : hit_kind_prev;
  assign sh_hit = (hit_kind_now == tinytracer_pkg::HIT_OBJECT) || (hit_kind_now == tinytracer_pkg::HIT_GROUND);
  assign sh_hit_ground = (hit_kind_now == tinytracer_pkg::HIT_GROUND);

  assign sh_checker_sel = ray_o.x[9] ^ ray_o.y[9];
  assign sample.valid = ((state == ST_SHADE) && sh_done && sh_path_end) || (state == ST_SAMPLE)
  assign sample.colour = sh_sample;

  // state FSM
  always_comb begin
    // raygen
    rg_start = 0;
    rg_mode = 0;

    // intersection unit
    iu_start = 0;
    iu_mode = 0;

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
          iu_mode = 0;
          iu_start = 1;
          next_state = IU_SEARCH;
        end
      end

      IU_SEARCH: begin
        if (iu_done) begin
          if ((iu_hit_kind == tinytracer_pkg::HIT_GROUND) && !sh_last_bounce) begin
            iu_start = 1;
            iu_mode = 2;
            next_state = IU_HIT_GND;
          end else begin
            // hits sky or object
            // or ground, when at bounce limit
            sh_start = 1;
            next_state = SH_SHADE;
          end
        end
      end

      IU_HIT_GND: begin // if the iu hit the ground
        if (iu_done) begin
          sh_start = 1;
          next_state = SH_SHADE;
        end
      end

      SH_SHADE: begin // shader core
        if (sh_done) begin
          if (sh_path_end) begin // last bounce logic handled here
            next_state = SAMPLE_WAIT; // finish sample, pass to accumulator
          end else if (hit_kind_prev == tinytracer_pkg::HIT_GROUND) begin
            // ! Note: From shader core instantiation, if path_end is 0, its either ground or object
            rg_start = 1;
            rg_mode = sh_material + 1; // feed next material to rg
            next_state = RG_MAT;
          end else begin
            iu_start = 1; // object still needs hit point and normal
            iu_mode = 2;
            next_state = IU_HIT;
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

      IU_HIT: begin // if it hit the object, calculate and save info into sram, then run bounce
        if (iu_done) begin
          rg_start = 1;
          rg_mode = sh_material + 1;
          next_state = RG_MAT;
        end
      end

      RG_MAT: begin // bounce based on material
        if (rg_done) begin
          next_state = IU_SEARCH;
          iu_start = 1;
          iu_mode = 0;
        end
      end

      default: begin
        next_state = IDLE;
      end

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
      mode <= 0;
      sh_new_sample <= 0;
    end else begin
      // sample initialization logic
      if (sample_start) begin
        bounce_cnt <= 0;
        sh_new_sample <= 1;
        atten <= 255;
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

  logic [4:0] bv_num;

  logic[4:0] hdr_idx;
  logic hdr_pending, hdr_sram_valid, hdr_finish, hdr_req_valid;
  logic [tinytracer_pkg::ADDR_WIDTH - 1: 0] hdr_req_addr;
  logic rg_active, iu_active, sc_active, ctrl_active;

  assign hdr_sram_valid = (state == HDR) && hdr_pending && sram.resp_valid;
  assign hdr_finish = hdr_sram_valid && (hdr_idx == (tinytracer_pkg::HDR_WORDS - 1));

  assign rg_active = (active == tinytracer_pkg::BLK_RAY_GEN);
  assign iu_active = (active == tinytracer_pkg::BLK_ISECT);
  assign sc_active = (active == tinytracer_pkg::BLK_SHADER);
  assign ctrl_active = (active == tinytracer_pkg::BLK_CTRL);

  // logic for reading next hdr_idx
  always_comb begin
    hdr_req_valid = 0;
    hdr_req_addr = hdr_idx;
    if (state == HDR) begin
      if (!hdr_pending) begin
        hdr_req_valid = 1;
      end else if (sram.resp_valid && (hdr_idx != (tinytracer_pkg::HDR_WORDS - 1))) begin
        // if valid, move to next hdr word
        hdr_req_valid = 1;
        hdr_req_addr = hdr_idx + 1;
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
          hdr_idx  <= hdr_idx + 1;
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
      scratch <= 0;
      // ! TODO: Check IU flip

    end else begin
      // update ray state raygen regs
      if (rg_o_we && rg_active) ray_o <= rg_o_wdata;
      if (rg_d_we && rg_active) ray_d <= rg_d_wdata;
      // ! TODO: how is ray_n written by IU? How and where does IU store anything in SRAM

      // scratch regs updates
      for (int i = 0; i < tinytracer_pkg::SCRATCH_WORDS; i++) begin
        if (rg_active && rg_scratch_we[i])
          scratch[i*tinytracer_pkg::WLEN +: tinytracer_pkg::WLEN] <= rg_scratch_wdata;
        // ! TODO: Check how scratch updates from IU
      end
    end
  end

  // SRAM read/req logic
  assign sram.resp_ready = 1; // keeps resp_ready high

  assign iu_sram.resp_rdata = sram.resp_rdata;
  assign sh_sram_valid = sram.resp_valid && sc_active;

  // The shader core pulses sram_rd for one cycle and holds sram_addr until the word is back
  logic sh_rd_pending;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      sh_rd_pending <= 0;
    end else if (sram.req_ready) begin
      sh_rd_pending <= 0;
    end else if (sc_active && sh_sram_rd) begin
      sh_rd_pending <= 1;
    end
  end

  // sram mux
  always_comb begin
    sram.req_valid = 0;
    sram.req_raddr = 0;
    iu_sram.req_ready = 0;
    iu_sram.resp_valid = 0;

    if (ctrl_active) begin
      sram.req_valid = hdr_req_valid;
      sram.req_raddr = hdr_req_addr;
    end else if (iu_active) begin
      sram.req_valid = iu_sram.req_valid;
      sram.req_raddr = iu_sram.req_raddr;
      iu_sram.req_ready = sram.req_ready;
      iu_sram.resp_valid = sram.resp_valid;
    end else if (sc_active) begin
      sram.req_valid = sh_sram_rd || sh_rd_pending;
      sram.req_raddr = sh_sram_addr;
    end
  end

  // request path
  logic [7:0] req_we;
  tinytracer_pkg::fmt_t req_fmt;
  tinytracer_pkg::vec3_t req_u, req_v;
  tinytracer_pkg::macro_op_t req_op;
  logic req_resize, req_valid;

  always_comb begin
    // ! Note: can optimize some of these default mux values by setting some of these to default to ray_gen
    req_we = 0;
    req_fmt = 0;
    req_u = 0;
    req_v = 0;
    req_resize = 0;
    req_valid = 0;
    req_op = 0;
    case (active)
      tinytracer_pkg::BLK_RAY_GEN: begin
        req_we     = rg_req.req_we;
        req_fmt    = rg_req.req_fmt;
        req_u      = rg_req.req_u;
        req_v      = rg_req.req_v;
        req_resize = rg_req.req_resize;
        req_op     = rg_req.req_op;
        req_valid  = rg_req.req_valid;
      end

      tinytracer_pkg::BLK_ISECT: begin
        req_we     = iu_req.req_we;
        req_fmt    = iu_req.req_fmt;
        req_u      = iu_req.req_u;
        req_v      = iu_req.req_v;
        req_resize = iu_req.req_resize;
        req_op     = iu_req.req_op;
        req_valid  = iu_req.req_valid;
      end

      tinytracer_pkg::BLK_SHADER: begin
        req_valid  = sh_req_valid;
      end

      // ! Note: no request path is used for shader core
      default: ;
    endcase
  end

  // request register
  tinytracer_pkg::macro_word_t req_reg, req_next;

  always_comb begin
    // ! TODO: code request resize here
    req_next = req_reg; // default to hold the same vals
    if (sc_active) begin
      if (sh_req_valid) req_next = sh_req_op; // shader core writes the whole word
    end else begin
      if (req_we[7]) req_next.fmt = req_fmt;
      if (req_we[6]) req_next.u.z = req_u.z; // u3
      if (req_we[5]) req_next.u.y = req_u.y; // u2
      if (req_we[4]) req_next.u.x = req_u.x; // u1
      if (req_we[3]) req_next.v.z = req_v.z; // v3
      if (req_we[2]) req_next.v.y = req_v.y; // v2
      if (req_we[1]) req_next.v.x = req_v.x; // v1
      if (req_we[0]) req_next.op  = req_op; // MACROOP
    end
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      req_reg <= 0;
    end else begin
      req_reg <= req_next;
    end
  end

  // Macro Ops
  assign macro.req_valid = req_valid;
  assign macro.req_op = req_next;
  assign macro.resp_ready = 1;

  assign rg_req.req_ready = macro.req_ready;
  assign rg_req.resp_valid = macro.resp_valid && rg_active;
  assign rg_req.resp_flag = macro.resp_result.x[0];
  assign rg_req.resp_result = macro.resp_result;

  assign iu_req.req_ready = macro.req_ready;
  assign iu_req.resp_valid = macro.resp_valid && iu_active;
  assign iu_req.resp_flag = macro.resp_result.x[0];
  assign iu_req.resp_result = macro.resp_result;

  assign sh_resp_valid = macro.resp_valid && sc_active;

  // ! TODO: code the size shift in request

endmodule
