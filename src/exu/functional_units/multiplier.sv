`default_nettype wire

module multiplier (
    input  logic        clk,
    input  logic        rst_n,
    
    // FU <-> Multiplier Interface
    fu_if.server        fu     
);

endmodule
