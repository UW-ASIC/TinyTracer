`default_nettype wire

module clkdiv (
    input  logic       clk,
    input  logic       rst_n,

    input  logic [7:0] b,
    input  logic [7:0] c,
    output logic       q
);

reg [ACCW-1:0] sr;

always @(posedge clk) begin
    if (!rst_n) begin
        sr <= {ACCW{1'b0}}; 
        q <= 0;
    end else if (sr[ACCW-1]) begin
        sr <= sr + b;
        q <= ~q;
    end else sr <= sr - c;
end


endmodule
