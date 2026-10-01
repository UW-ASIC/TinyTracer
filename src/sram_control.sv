`default_nettype wire

module sram_control (
    input  logic                              clk,
    input  logic                              rst_n,

    // I/O <-> SRAM Interface
    sram_wr_if.server                         io_wr,

    // RTU <-> SRAM Interface
    sram_rd_if.server                         rtu_rd,

    // SRAM Control Signals
    output logic                              wen,
    output logic [tinytracer_pkg::ADDR_WIDTH-1:0]             addr,
    output logic [tinytracer_pkg::DATA_WIDTH-1:0]             din,
    input  logic [tinytracer_pkg::DATA_WIDTH-1:0]             dout
);

endmodule
