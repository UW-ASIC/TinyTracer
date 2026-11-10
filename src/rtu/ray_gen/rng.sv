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

    /* Above unrolls into this, can test both to compare (but below uses fixed TAPS=x100B and W=16)
    They should practically be the same (but the for loop is nicer to look at)
    assign lfsr_next[ 0] = lfsr[0] ^ lfsr[4] ^ lfsr[8] ^ lfsr[12] ^ lfsr[13] ^ lfsr[15];
    assign lfsr_next[ 1] = lfsr[0] ^ lfsr[1] ^ lfsr[4] ^ lfsr[5] ^ lfsr[8] ^ lfsr[9] ^ lfsr[12] ^ lfsr[14] ^ lfsr[15];
    assign lfsr_next[ 2] = lfsr[1] ^ lfsr[2] ^ lfsr[5] ^ lfsr[6] ^ lfsr[9] ^ lfsr[10] ^ lfsr[13] ^ lfsr[15];
    assign lfsr_next[ 3] = lfsr[0] ^ lfsr[2] ^ lfsr[3] ^ lfsr[4] ^ lfsr[6] ^ lfsr[7] ^ lfsr[8] ^ lfsr[10] ^ lfsr[11] ^ lfsr[12] ^ lfsr[13] ^ lfsr[14] ^ lfsr[15];
    assign lfsr_next[ 4] = lfsr[1] ^ lfsr[3] ^ lfsr[4] ^ lfsr[5] ^ lfsr[7] ^ lfsr[8] ^ lfsr[9] ^ lfsr[11] ^ lfsr[12] ^ lfsr[13] ^ lfsr[14] ^ lfsr[15];
    assign lfsr_next[ 5] = lfsr[2] ^ lfsr[4] ^ lfsr[5] ^ lfsr[6] ^ lfsr[8] ^ lfsr[9] ^ lfsr[10] ^ lfsr[12] ^ lfsr[13] ^ lfsr[14] ^ lfsr[15];
    assign lfsr_next[ 6] = lfsr[3] ^ lfsr[5] ^ lfsr[6] ^ lfsr[7] ^ lfsr[9] ^ lfsr[10] ^ lfsr[11] ^ lfsr[13] ^ lfsr[14] ^ lfsr[15];
    assign lfsr_next[ 7] = lfsr[4] ^ lfsr[6] ^ lfsr[7] ^ lfsr[8] ^ lfsr[10] ^ lfsr[11] ^ lfsr[12] ^ lfsr[14] ^ lfsr[15];
    assign lfsr_next[ 8] = lfsr[5] ^ lfsr[7] ^ lfsr[8] ^ lfsr[9] ^ lfsr[11] ^ lfsr[12] ^ lfsr[13] ^ lfsr[15];
    assign lfsr_next[ 9] = lfsr[6] ^ lfsr[8] ^ lfsr[9] ^ lfsr[10] ^ lfsr[12] ^ lfsr[13] ^ lfsr[14];
    assign lfsr_next[10] = lfsr[7] ^ lfsr[9] ^ lfsr[10] ^ lfsr[11] ^ lfsr[13] ^ lfsr[14] ^ lfsr[15];
    assign lfsr_next[11] = lfsr[8] ^ lfsr[10] ^ lfsr[11] ^ lfsr[12] ^ lfsr[14] ^ lfsr[15];
    assign lfsr_next[12] = lfsr[0] ^ lfsr[4] ^ lfsr[8] ^ lfsr[9] ^ lfsr[11];
    assign lfsr_next[13] = lfsr[1] ^ lfsr[5] ^ lfsr[9] ^ lfsr[10] ^ lfsr[12];
    assign lfsr_next[14] = lfsr[2] ^ lfsr[6] ^ lfsr[10] ^ lfsr[11] ^ lfsr[13];
    assign lfsr_next[15] = lfsr[3] ^ lfsr[7] ^ lfsr[11] ^ lfsr[12] ^ lfsr[14];
    */

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            lfsr <= SEED;     // Doc specifies always reset to 'b1, assume SEED will always be 'b1
        end else if (req) begin
            lfsr <= lfsr_next;
        end
    end
    assign rand_num = lfsr;
    
endmodule
