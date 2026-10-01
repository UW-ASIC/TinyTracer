`default_nettype wire

module alu (
    input  logic        clk,
    input  logic        rst_n,
    
    // FU <-> ALU Interface
    fu_if.server        fu       
);

endmodule
