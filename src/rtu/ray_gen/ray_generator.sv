`default_nettype wire

// Makes the camera ray of each sample and the new ray after each bounce. The
// RTU owns the shared registers: the Ray Generator reads them on input ports,
// builds its macro-op operands from them, and writes O, D, and scratch words
// through its write ports (see docs/modules/rtu/ray_gen/ray_generator.md).
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

endmodule
