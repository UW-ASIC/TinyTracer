`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module multiplier (
    input  logic        clk,
    input  logic        rst_n,
    
    // FU <-> Multiplier Interface
    fu_if.server        fu     
);

endmodule
