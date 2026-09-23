`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module uart (
    input  logic       clk,
    input  logic       rst_n,

    input  logic       clkq,

    // UART <-> I/O Interface
    stream_if.src      rx,      // receive byte stream, to I/O
    stream_if.sink     tx,      // transmit byte stream, from I/O

    // UART <-> Host Device Interface
    input  logic       TT_RX,
    output logic       TT_TX
);

endmodule
