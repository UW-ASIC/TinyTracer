`default_nettype wire

module reg_file (
    input  logic        clk,
    input  logic        rst_n,

    // Parallel Load (Decode): R0-R2 <- load_u.{x,y,z}, R3-R5 <- load_v.{x,y,z}
    input  logic                   load,
    input  tinytracer_pkg::vec3_t  load_u,
    input  tinytracer_pkg::vec3_t  load_v,

    // Macro-op Result (Decode): {R2, R1, R0}
    output tinytracer_pkg::vec3_t  result,

    // Write Port (FU Control)
    input  logic            wen,
    input  logic [2:0]      waddr,
    input  logic [tinytracer_pkg::WLEN-1:0] wdata,

    // Read Ports (FU Control)
    input  logic [2:0]      raddr1,
    output logic [tinytracer_pkg::WLEN-1:0] rdata1,
    input  logic [2:0]      raddr2,
    output logic [tinytracer_pkg::WLEN-1:0] rdata2
);

endmodule
