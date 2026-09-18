`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module rtu (
    input  logic        clk,
    input  logic        rst_n,

    input  logic        render,

    // RTU <-> SRAM Interface
    sram_rd_if.client   sram,

    // RTU <-> Decode Interface
    macro_if.client     macro,

    // RTU <-> Accumulator Interface
    colour_if.src       sample    // sample colour stream, to Accumulator
);

endmodule
