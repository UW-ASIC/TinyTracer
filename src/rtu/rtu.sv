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
  logic [1:0]                sh_mode;
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
  rtu_req_if sh_req ();

  // Intersection Unit SRAM reads, connected to sram while it is active
  sram_rd_if iu_sram ();

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
  shader_core u_shader_core (
      .clk    (clk),
      .rst_n  (rst_n),
      .start  (sh_start),
      .mode   (sh_mode),
      .done   (sh_done),
      .req    (sh_req),
      .sample (sample)
  );

  // actual rtl part
  // IDLE: idle state, waiting for render signal
  // HDR: loads header signals
  // RG_CAM: ray generator camera ray (step 1 in docs)
  // IU_SEARCH: intersection unit search (step 2)
  // SH_SKY: Shader core sky (step 3)
  // IU_READ: intersection unit read (step 4)
  // SH_LIMIT: shader core bounce (if bounce count over 8) -> maybe combine with IU_HIT
  // IU_HIT: intersection unit hits (if bounce count less than 8)
  // SH_GLOW: shader core glow sample
  // SH_ATTN: shader core attenuation
  // RG_MAT: ray generator material -> check if different mats need diff state


  typedef enum logic [3:0] { IDLE, HDR, RG_CAM, IU_SEARCH, SH_SKY, IU_READ, SH_LIMIT, IU_HIT, SH_GLOW, SH_ATTN, RG_MAT } ctrl_state;
  ctrl_state state, next_state;

  // header registers
  logic [4:0] sample_cnt;

  logic [3:0] bounce_cnt;
  logic [7:0] atten;
  logic [4:0] max_samples; // max of spp_log2 is 32, so 5 bits is needed
  logic last_col, last_row;
  logic sample_start, sample_done, frame_done, final_sample;

  assign max_samples = (1 << spp_log2) - 1; // number of samples to count to per pixel
  assign last_col = (pix_x == (img_w - 1)); // pixel on right border
  assign last_row = (pix_y == (img_h - 1)); // pixel on bottom
  assign at_limit = (bounce_cnt == tinytracer_pkg::MAX_BOUNCES);
  assign final_sample = (sample_cnt == max_samples);

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
    sh_mode = 0;

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
          rg_mode = 0;
          rg_start = 1;
          next_state = RG_CAM;
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
          case (iu_hit_kind)
            tinytracer_pkg::HIT_SKY: begin
              next_state = SH_SKY;
              sh_start = 1;
              sh_mode = 0;
            end
            tinytracer_pkg::HIT_OBJECT: begin
              next_state = IU_READ;
              iu_start = 1;
              iu_mode = 1;
            end
            tinytracer_pkg::HIT_GROUND: begin
              if (at_limit) begin
                next_state = SH_LIMIT;
                sh_mode = 3;
                sh_start = 1;
              end else begin
                next_state = IU_HIT;
                iu_mode = 2;
                iu_start = 1;
              end
            end
          endcase
        end
      end

      SH_SKY: begin
        if (sh_done) begin
          sample_done = 1;
        end
      end

      IU_READ: begin
        if (iu_done) begin
          if (iu_material == tinytracer_pkg::MAT_EMISSIVE) begin
            // glow sample
            next_state = SH_GLOW;
            sh_start = 1;
            sh_mode = 1;
          end else begin
            // non-glow sample
            // maybe move this to a separate signal
            if (at_limit) begin
              next_state = SH_LIMIT;
              sh_mode = 3;
              sh_start = 1;
            end else begin
              next_state = IU_HIT;
              iu_mode = 2;
              iu_start = 1;
            end
          end
        end
      end

      SH_LIMIT: begin
        if (sh_done) begin
          sample_done = 1;
        end
      end

      IU_HIT: begin
        if (iu_done) begin
          next_state = SH_ATTN;
          sh_start = 1;
          sh_mode = 2;
        end
      end

      SH_GLOW: begin
        if (sh_done) begin
          sample_done = 1;
        end
      end

      SH_ATTN: begin
        if (sh_done) begin
          next_state = RG_MAT;
          rg_start = 1;
          rg_mode = iu_material + 1;
        end
      end

      RG_MAT: begin
        next_state = IU_SEARCH;
        iu_start = 1;
        iu_mode = 0;
        bounce_cnt = bounce_cnt + 1;
      end

      default: begin
        next_state = IDLE;
      end

    endcase
    
    // combinational state logic for finished samples
    if (sample_done) begin
      if (last_col && last_row && final_sample) begin // if at last pixel and sample count is maxxed, reset the states
        if (final_sample) begin
          frame_done = 1;
          next_state = IDLE;
        end else begin
          sample_start = 1;
          rg_mode = 0;
          rg_start = 1;
          next_state = RG_CAM;
        end
      end
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
    end else begin
      // sample initialization logic
      if (sample_start) begin
        bounce_cnt <= 0;
        atten <= 8'd255;
      end

      // counter resetting
      if (state == IDLE && render.render) begin
        pix_x      <= '0;
        pix_y      <= '0;
        sample_cnt <= '0;
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
            end // TODO: doublecheck if anything needs to be done here
          end
        end
      end

      // TODO: check if hit kind changes material type, or if thats handled in IU
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

  tinytracer_pkg::rgb_t sky_hor, sky_top, gnd_a, gnd_b;
  logic [4:0] bv_num;

  logic[4:0] hdr_idx;
  logic hdr_pending, hdr_sram_valid, hdr_finish;

  assign hdr_sram_valid = (state == HDR) && hdr_pending && sram.resp_valid;
  assign hdr_finish = hdr_sram_valid && (hdr_idx == (tinytracer_pkg::HDR_WORDS - 1))

  // header index counter logic
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      hdr_idx  <= '0;
      hdr_pending <= 1'b0;
    end else if (state == IDLE) begin // on sample finishes. kept separate to distinguish
      hdr_idx  <= '0;
      hdr_pending <= 1'b0;
    end else if (state == HDR) begin
      if (!hdr_pending) begin
        if (sram.req_ready) hdr_pending <= 1'b1; // TODO: double check timings
      end else if (sram.resp_valid) begin
        if (hdr_idx != 5'(tinytracer_pkg::HDR_WORDS - 1)) begin
          hdr_idx  <= hdr_idx + 5'd1;
          hdr_pending <= sram.req_ready;   // next request accepted in this cycle, or retry
        end else begin
          hdr_pending <= 1'b0; // resets on next cycle
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

  // TODO: implement SRAM connection to IU, SC
  // TODO: deal with ray state regs
  // TODO: deal with request path and its handshakes
  // TODO: deal with rng module

endmodule
