`default_nettype wire

// Galois LFSR random number generator (see docs/modules/rtu/ray_gen/rng.md).
module rng #(
    parameter [tinytracer_pkg::WLEN-1:0] SEED = 16'h0001,  // Reset value; any nonzero value works
    parameter [tinytracer_pkg::WLEN-1:0] TAPS = 16'h100B   // XOR tap locations
) (
    input  logic            clk,
    input  logic            rst_n,

    // Ray Generator <-> RNG Signals
    input  logic            req,       // Shift the LFSR to produce a new random number
    output logic [tinytracer_pkg::WLEN-1:0] rand_num   // Current LFSR state
);

endmodule
