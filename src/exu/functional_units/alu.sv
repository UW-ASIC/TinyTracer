`default_nettype wire
module alu #(
    parameter WLEN = 5'd16
)
(
    // inputs
    input  logic        clk,
    input  logic        rst_n,
    
    // FU <-> ALU Interface
    fu_if.server        fu       
);

always_ff @ (posedge clk or negedge rst_n) begin
    // reset logic
    if (!rst_n) begin
        fu.req_ready <= 0;
        fu.resp_done <= 0;
        fu.resp_result <= 0;
    end else if (fu.req_valid) begin
        case (fu.req_opcode)
            // check back in on signedness..
            ALU_ADD : begin
                fu.req_ready <= 1
                fu.resp_done <= 1
                reg_result <= (fu.req_op1 > 16'h7FFF - fu.req_op2) ? 16'h7FFF : (fu.req_op1 + fu.req_op2);
            end
            ALU_SUB : begin
                fu.req_ready <= 1
                fu.resp_done <= 1
                reg_result <= (fu.req_op1 < 16'h8000 + fu.req_op2) ? 16'h7FFF : (fu.req_op1 - fu.req_op2);
            end
            ALU_EQ : begin
                fu.req_ready <= 1
                fu.resp_done <= 1
                reg_result <= (fu.req_op1 == fu.req_op2) ? 16'h0001 : 16'h8000
            end
            ALU_NE : begin
                fu.req_ready <= 1
                fu.resp_done <= 1
                reg_result <= (fu.req_op1 == fu.req_op2) ? 16'h8000 : 16'h0001
            end
            ALU_LT : begin
                fu.req_ready <= 1
                fu.resp_done <= 1
                reg_result <= (fu.req_op1 < fu.req_op2) ? 16'h0001 : 16'h8000
            end
            ALU_GE : begin
                fu.req_ready <= 1
                fu.resp_done <= 1
                reg_result <= (fu.req_op1 < fu.req_op2) ? 16'h8000 : 16'h0001
            end
            default: begin
                fu.req_ready <= 1
                fu.resp_done <= 1
                reg_result <= (fu.req_op1 > 16'h7FFF - fu.req_op2) ? 16'h7FFF : (fu.req_op1 + fu.req_op2);
            end
        endcase
    end else begin
        fu.req_ready <= 1
    end
end


endmodule
