`default_nettype wire
// No package import: the UART only depends on its own parameters and stream_if.
// The defaults below still come from the package, so it stays the single source
// of truth for the system clock and baud rate.

module uart #(
    // Deliberately named like the package constants they default to; the
    // unit-scope imports in other files make Verilator see them as hidden.
    /* verilator lint_off VARHIDDEN */
    parameter int FCLK = tinytracer_pkg::FCLK,  // system clock frequency (Hz)
    parameter int BAUD = tinytracer_pkg::BAUD   // UART baud rate
    /* verilator lint_on VARHIDDEN */
) (
    input  logic       clk,
    input  logic       rst_n,

    // UART <-> I/O Interface
    stream_if.src      rx,      // receive byte stream, to I/O
    stream_if.sink     tx,      // transmit byte stream, from I/O

    // UART <-> Host Device Interface
    input  logic       TT_RX,
    output logic       TT_TX
);

endmodule
