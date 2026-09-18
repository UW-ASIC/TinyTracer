`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module decode (
    input  logic        clk,
    input  logic        rst_n,

    // RTU <-> Decode Interface
    macro_if.server     macro,

    // Decode <-> FU Interface
    micro_if.client     micro,

    // Register File Port
    reg_file_if.user    rf
);

endmodule
