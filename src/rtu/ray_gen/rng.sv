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

    localparam int W = tinytracer_pkg::WLEN;     // For ease of use
    logic [W-1:0] lfsr, lfsr_next;     // Isolate internal states from output

    always_comb begin
        lfsr_next = lfsr;
        for (int i = 0; i < W; i++)     // Unrolls to shift 16 times
            lfsr_next = {lfsr_next[W-2:0], 1'b0} ^ ({W{lfsr_next[W-1]}} & TAPS);    // Implementation of state <= state[msb] ? state_shifted ^ taps : state_shifted
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            lfsr <= SEED;     // Doc specifies always reset to 'b1, assume SEED will always be 'b1
        end else if (req) begin
            lfsr <= lfsr_next;
        end
    end
    assign rand_num = lfsr;
    
endmodule
