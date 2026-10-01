`default_nettype wire

module decode (
    input  logic        clk,
    input  logic        rst_n,

    // RTU <-> Decode Interface (passed through by the EXU)
    macro_if.server     macro,

    // Decode <-> FU Interface
    micro_if.client     micro,

    // Register File Ports: rf_load loads the macro-op operands in the cycle
    // the macro-op is accepted; rf_result drives the macro-op result.
    output logic                   rf_load,
    input  tinytracer_pkg::vec3_t  rf_result
);

endmodule
