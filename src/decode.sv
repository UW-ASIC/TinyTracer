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

    // Register File Ports (write port for INITIALIZE, read port 1 for LOAD)
    output logic            rf_wen,
    output logic [2:0]      rf_waddr,
    output logic [WLEN-1:0] rf_wdata,
    output logic [2:0]      rf_raddr,
    input  logic [WLEN-1:0] rf_rdata
);

endmodule
