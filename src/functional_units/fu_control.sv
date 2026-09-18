`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module fu_control (
    input  logic        clk,
    input  logic        rst_n,

    // Register File Port
    reg_file_if.user    rf,

    // Micro-op Channel
    micro_if.server     micro,
    
    // FU <-> SRAM Interface
    sram_rd_if.client   cordic_sram
);

endmodule
