`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module reg_file (
    input  logic        clk,
    input  logic        rst_n,

    // Single Read/Write Port
    reg_file_if.mem     rf
);

endmodule
