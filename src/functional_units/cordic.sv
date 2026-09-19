`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module cordic #(
    parameter int ITER=WLEN
) (
    input  logic        clk,
    input  logic        rst_n,

    // FU <-> CORDIC Interface
    fu_if.server        fu
);

endmodule
