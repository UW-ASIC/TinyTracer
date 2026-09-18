`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module accumulator (
    input  logic        clk,
    input  logic        rst_n,

    // RTU <-> Accumulator Interface
    colour_if.sink      sample,   // sample colour stream, from RTU

    // Accumulator <-> I/O Interface
    colour_if.src       pixel     // pixel colour stream, to I/O
);

endmodule
