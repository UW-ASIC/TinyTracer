`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module xorshift_rng #(
    parameter [WLEN-1:0] SEED = 16'hACE1  // If word length ever changes from 16, use a different seed of length WLEN
) (
    input  logic        clk,
    input  logic        rst_n,
    
    // FU <-> RNG Interface
    fu_if.server        fu     
);

endmodule
