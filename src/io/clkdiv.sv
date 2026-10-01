`default_nettype wire

module clkdiv (
    input  logic       clk,
    input  logic       rst_n,

    input  logic [7:0] b,
    input  logic [7:0] c,
    output logic       q
);

reg [7:0] sr;
wire [7:0] d;

assign d = sr[7] ? b : c;

always @(posedge clk) begin
    if (!rst_n) begin
        sr <= 0;
        q <= 0;
    end else  begin
        sr <= sr + d;
        if (sr[7]) begin
            q <= ~q;
        end
    end
end

endmodule
