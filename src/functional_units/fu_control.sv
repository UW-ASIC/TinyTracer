`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module fu_control (
    input  logic        clk,
    input  logic        rst_n,

    // Register File Ports (both read ports for operands, write port for results)
    output logic            rf_wen,
    output logic [2:0]      rf_waddr,
    output logic [WLEN-1:0] rf_wdata,
    output logic [2:0]      rf_raddr1,
    input  logic [WLEN-1:0] rf_rdata1,
    output logic [2:0]      rf_raddr2,
    input  logic [WLEN-1:0] rf_rdata2,

    // Micro-op Channel
    micro_if.server     micro
);

endmodule
