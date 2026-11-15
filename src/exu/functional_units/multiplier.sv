`default_nettype wire

module multiplier (
    input  logic        clk,
    input  logic        rst_n,
    
    // FU <-> Multiplier Interface
    fu_if.server        fu     
);

// Signed 16 bit operands from FU
logic signed [15:0] op1;
logic signed [15:0] op2;


logic [31:0] product_mag; // Unsigned magnitude of multiplication result
logic product_sign; // 0 = positive, 1 = negative
logic [15:0] multiplicand; // Magnitude op1
logic [15:0] multiplier; // Magnitude op2
logic [15:0] partial_product [0:15]; // Partial product generated for each bit of multiplicand
logic signed [31:0] signed_product; // Signed result after final sign reapplied
logic [31:0] shifted_rounded_result; // Positive magnitude after shifting and rounding
logic signed [15:0] final_result; // Final 16 bit result to be returned to FU

// Prepare inputs for multiplier
always_comb begin
    op1 = $signed(fu.req_op1);
    op2 = $signed(fu.req_op2);

    // Product is negative if 1 operand negative
    product_sign = op1[15] ^ op2[15];
    multiplicand = op1[15] ? -op1 : op1; // If MSB high convert to positive magnitude
    multiplier = op2[15] ? -op2 : op2;
end

// Generate 16 partial products
genvar i;
generate 
    for (i = 0; i < 16; i++) begin : generate_ppg
        assign partial_product[i] = multiplier & {16{multiplicand[i]}};
    end
endgenerate

always_comb begin 
    product_mag = 32'b0;

    // Shift each partial product to the correct position and then sum them all to get final 32 bit result
    int i;
    for (i = 0; i < 16; i++) begin
        product_mag = product_mag + ({16'b0, partial_product[i]} << i); // extend partial product to be 32 bits
    end

    // Shift based on fmt
    if (fu.req_fmt == 1'b0) begin
        shifted_rounded_result = (product_mag + 32'd64) >> 7;
    end else begin
        shifted_rounded_result = (product_mag + 32'd8192) >> 14;
    end

    // Create the signed product
    if (product_sign) begin
        signed_product = -$signed(shifted_rounded_result);
    end else begin
        signed_product = $signed(shifted_rounded_result);
    end

    // Clamp the result to 16'h7FFF or 16'h8000 (check whether the shifted rounded result fits in a signed 16 bit value)
    // Min value = -2^15, Max value = 2^15 - 1
    if (signed_product > 32767) begin
        final_result = 16'h7FFF;
    end else if (signed_product < -32768) begin
        final_result = 16'h8000;
    end else begin
        final_result = signed_product[15:0];
    end

    fu.resp_result = final_result;

end 

endmodule
