`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module shader_core (
    input  logic                            clk,
    input  logic                            rst_n,

    input  tinytracer_pkg::rgb_t            sky_colour,
    input  tinytracer_pkg::rgb_t            object_colour,
    input  tinytracer_pkg::mat_type_t       mat_type,
    input  logic [$clog2(MAX_BOUNCES)-1:0]  ray_bounces_left,
    input  logic                            hit,

    // RTU <-> Accumulator Interface
    colour_if.src                           sample,   // sample colour stream, to Accumulator

    // RTU <-> Decode Interface
    macro_if.client                         macro
);

endmodule
