`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module rtu (
    input  logic        clk,
    input  logic        rst_n,

    // I/O <-> RTU Interface
    render_if.sink      render,   // render strobe and image dimensions, from I/O

    // RTU <-> SRAM Interface
    sram_rd_if.client   sram,

    // RTU <-> Decode Interface
    macro_if.client     macro,

    // RTU <-> Accumulator Interface
    colour_if.src       sample    // sample colour stream, to Accumulator
);

endmodule
