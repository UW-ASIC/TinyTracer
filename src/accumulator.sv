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

// definitions
logic[tinytracer_pkg::SAMPLE_DEPTH+$clog2(tinytracer_pkg::MAX_SPP)-1:0] accumulator_r;
logic[tinytracer_pkg::SAMPLE_DEPTH+$clog2(tinytracer_pkg::MAX_SPP)-1:0] accumulator_g;
logic[tinytracer_pkg::SAMPLE_DEPTH+$clog2(tinytracer_pkg::MAX_SPP)-1:0] accumulator_b;

logic [$clog2(tinytracer_pkg::MAX_SPP):0]count;
// added to fix potential bug with missing samples
wire [$clog2(tinytracer_pkg::MAX_SPP):0] next_count = count + 1'b1;
// _____________________________________________

// combinational logic 

logic [tinytracer_pkg::COLOUR_DEPTH-1:0] r_valid, g_valid, b_valid;
logic [tinytracer_pkg::SAMPLE_DEPTH+$clog2(tinytracer_pkg::MAX_SPP)-1:0] r_shifted, g_shifted, b_shifted;

always_comb begin 
    r_shifted = accumulator_r >> spp_log2;
    g_shifted = accumulator_g >> spp_log2;
    b_shifted = accumulator_b >> spp_log2;

    r_valid = (r_shifted > 'd255) ? 8'd255 : r_shifted[tinytracer_pkg::COLOUR_DEPTH-1:0];
    g_valid = (g_shifted > 'd255) ? 8'd255 : g_shifted[tinytracer_pkg::COLOUR_DEPTH-1:0];
    b_valid = (b_shifted > 'd255) ? 8'd255 : b_shifted[tinytracer_pkg::COLOUR_DEPTH-1:0];
    
    pixel.colour = {r_valid, g_valid, b_valid};
end
// _____________________________________________
always_ff @(posedge clk or negedge rst_n) begin

if (!rst_n) begin
        // reset block
    count <= '0;
    accumulator_r <= '0;
    accumulator_g <= '0;
    accumulator_b <= '0;
    pixel.valid <= 1'b0;
    sample.ready <= 1'b1;

end 

// after downstream accepts, get ready for next
else if(pixel.valid && pixel.ready) begin 
         // clear sums to move to next pixel
    accumulator_r <= '0;
    accumulator_g <= '0;
    accumulator_b <= '0;
    pixel.valid <= 1'b0;
    sample.ready <= 1'b1;
    count <= '0;

end
// start transmission
else if(sample.valid && sample.ready) begin 

    accumulator_r <= accumulator_r + sample.colour[3*tinytracer_pkg::SAMPLE_DEPTH-1:2*tinytracer_pkg::SAMPLE_DEPTH]; // r
    accumulator_g <= accumulator_g + sample.colour[2*tinytracer_pkg::SAMPLE_DEPTH-1:tinytracer_pkg::SAMPLE_DEPTH]; // g
    accumulator_b <= accumulator_b + sample.colour[tinytracer_pkg::SAMPLE_DEPTH-1:0]; // b
    // change made due to potential bug with missed samples
    count <= next_count;
    if (next_count[spp_log2]) begin // after accumulating s samples
    sample.ready <= 1'b0;
    pixel.valid <= 1'b1;
    end


end
    

end

endmodule