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

endmodule
