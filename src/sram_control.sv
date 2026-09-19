`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module sram_control (
    input  logic                              clk,
    input  logic                              rst_n,

    // I/O <-> SRAM Interface
    sram_wr_if.server                         io_wr,

    // RTU <-> SRAM Interface
    sram_rd_if.server                         rtu_rd,

    // SRAM Control Signals
    output logic                              wen,
    output logic                              bank_sel,
    output logic [ADDR_WIDTH-BANK_WIDTH-1:0]  addr,
    output logic [DATA_WIDTH-1:0]             din,
    input  logic [DATA_WIDTH-1:0]             dout
);

endmodule
