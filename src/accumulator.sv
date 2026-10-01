`default_nettype wire

module accumulator (
    input  logic        clk,
    input  logic        rst_n,

    // RTU <-> Accumulator Interface
    colour_if.sink      sample,   // sample colour stream (W = SAMPLE_DEPTH), from RTU
    input  logic [tinytracer_pkg::SPP_LOG2_W-1:0] spp_log2,  // log2(samples per pixel), from the RTU's header registers

    // Accumulator <-> I/O Interface
    colour_if.src       pixel     // pixel colour stream (W = COLOUR_DEPTH), to I/O
);

endmodule
