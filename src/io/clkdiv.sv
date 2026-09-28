`default_nettype wire

module clkdiv (
    input  logic       clk,
    input  logic       rst_n,

    input  logic [7:0] b,
    input  logic [7:0] c,
    output logic       q
);

reg [7:0] sr;

always @(posedge clk) begin
    if (!rst_n) begin
        sr <= {8'b0}; 
        q <= 0;
    end else if (sr[7]) begin
        sr <= sr + b;
        q <= ~q;
    end else sr <= sr - c;
end


endmodule
