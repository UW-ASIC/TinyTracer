`default_nettype wire

// Reads and writes the RTU's shared header and ray state registers; the
// signals for that and for operand source selects are not defined yet (see
// docs/modules/rtu/rtu.md, Handshakes).
module shader_core (
    input  logic                            clk,
    input  logic                            rst_n,

    // Controller <-> Shader Core Signals (start, done: one-cycle pulses)
    input  logic                            start,    // Start signal from the Controller; mode valid with it
    input  logic [1:0]                      mode,     // 0: sky sample, 1: glow sample, 2: surface (attenuation), 3: bounce limit
    output logic                            done,     // Attenuation updated (mode 2), or the Accumulator took the sample

    // Shader Core <-> RTU Request Path Interface
    rtu_req_if.client                       req,

    // RTU <-> Accumulator Interface
    colour_if.src                           sample    // sample colour stream (W = SAMPLE_DEPTH), to Accumulator
);

endmodule
