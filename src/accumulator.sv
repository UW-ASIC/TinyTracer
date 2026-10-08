`default_nettype wire

module accumulator 
import tinytracer_pkg::*;
(
    input  logic        clk,
    input  logic        rst_n,

    // RTU <-> Accumulator Interface
    colour_if.sink      sample,   // sample colour stream (W = SAMPLE_DEPTH), from RTU
    input  logic [tinytracer_pkg::SPP_LOG2_W-1:0] spp_log2,  // log2(samples per pixel), from the RTU's header registers

    // Accumulator <-> I/O Interface
    colour_if.src       pixel     // pixel colour stream (W = COLOUR_DEPTH), to I/O
);

// definitions
logic[SAMPLE_DEPTH+$clog2(MAX_SPP)-1:0] accumulator_r;
logic[SAMPLE_DEPTH+$clog2(MAX_SPP)-1:0] accumulator_g;
logic[SAMPLE_DEPTH+$clog2(MAX_SPP)-1:0] accumulator_b;

logic [$clog2(MAX_SPP):0]count;
logic samples_done;
assign samples_done = count[spp_log2];
// _____________________________________________

// combinational logic 

logic [COLOUR_DEPTH-1:0] r_valid, g_valid, b_valid;
    // calculate averages etc, need to do it always
    always_comb begin 
    
        r_valid = ((accumulator_r>>spp_log2) > 8'd255)? 8'd255: (accumulator_r>>spp_log2)[COLOUR_DEPTH-1:0] ;
        g_valid = ((accumulator_g>>spp_log2) > 8'd255)? 8'd255: (accumulator_g>>spp_log2)[COLOUR_DEPTH-1:0] ;
        b_valid = ((accumulator_b>>spp_log2) > 8'd255)? 8'd255: (accumulator_b>>spp_log2)[COLOUR_DEPTH-1:0] ;
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
// after accumulating s samples
else if(samples_done) 
begin
        // final pixels calculated outside
        // final pixels sent outside too
        // setting conditions
        pixel.valid <= 1'b1;
        // waiting for downstream to accept. cut off samples
        sample.ready <= 1'b0;

end 
// start transmission
else if(sample.valid && sample.ready) begin 

    accumulator_r <= accumulator_r + sample.colour[3*SAMPLE_DEPTH-1:2*SAMPLE_DEPTH]; // r
    accumulator_g <= accumulator_g + sample.colour[2*SAMPLE_DEPTH-1:SAMPLE_DEPTH]; // g
    accumulator_b <= accumulator_b + sample.colour[SAMPLE_DEPTH-1:0]; // b

    count <= count + 1'b1;


end
    

end

endmodule
