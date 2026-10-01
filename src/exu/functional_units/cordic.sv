`default_nettype wire

module cordic #(
    parameter int ITER=tinytracer_pkg::WLEN
) (
    input  logic        clk,
    input  logic        rst_n,

    // FU <-> CORDIC Interface
    fu_if.server        fu
);

endmodule
