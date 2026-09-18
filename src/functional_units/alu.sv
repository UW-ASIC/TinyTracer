`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module alu (
    input  logic        clk,
    input  logic        rst_n,
    
    // FU <-> ALU Interface
    fu_if.server        fu       
);

endmodule
