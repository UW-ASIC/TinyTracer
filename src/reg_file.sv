`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module reg_file (
    input  logic        clk,
    input  logic        rst_n,

    // Write Port
    input  logic            wen,
    input  logic [2:0]      waddr,
    input  logic [WLEN-1:0] wdata,

    // Read Ports
    input  logic [2:0]      raddr1,
    output logic [WLEN-1:0] rdata1,
    input  logic [2:0]      raddr2,
    output logic [WLEN-1:0] rdata2
);

endmodule
