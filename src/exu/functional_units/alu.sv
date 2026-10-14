`default_nettype wire
module alu #(
    parameter WLEN = 16
)
(
    // inputs
    input  logic        clk,
    input  logic        rst_n,
    
    // FU <-> ALU Interface
    fu_if.server        fu       
);

logic reg_req_valid;
logic signed [WLEN-1:0] reg_req_op1;
logic signed [WLEN-1:0] reg_req_op2;
logic [2:0] reg_req_opcode;

localparam signed [WLEN-1:0] MAX_CLAMP = {1'b0, {WLEN-1{1'b1}}};
localparam signed [WLEN-1:0] MIN_CLAMP = {1'b1, {WLEN-1{1'b0}}};
localparam signed [WLEN-1:0] SIGNED_ONE = {{WLEN-1{1'b0}}, 1'b1};

logic signed [WLEN:0] sum;
logic signed [WLEN:0] diff;

// buffer in inputs -> can add more stages if needed
always_ff @ (posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        reg_req_valid <= 0;
        reg_req_op1 <= 0;
        reg_req_op2 <= 0;
        reg_req_opcode  <= 0;
    end else begin
        reg_req_valid <= fu.req_valid;
        reg_req_op1 <= fu.req_op1;
        reg_req_op2 <= fu.req_op2;
        reg_req_opcode  <= fu.req_opcode;
    end
end

always_comb begin
    if (reg_req_valid) begin
        case (reg_req_opcode)
            ALU_ADD : begin
                // signed saturated add
                fu.resp_done <= 1;
                fu.resp_result <= (sum[WLEN:WLEN-1] == 2'b01) ? MAX_CLAMP : (sum[WLEN:WLEN-1] == 2'b10) ? MIN_CLAMP : sum[WLEN-1:0];
            end
            ALU_SUB : begin
                // signed saturated subtract
                fu.resp_done <= 1;
                fu.resp_result <= (diff[WLEN:WLEN-1] == 2'b01) ? MAX_CLAMP : (diff[WLEN:WLEN-1] == 2'b10) ? MIN_CLAMP : diff[WLEN-1:0];
            end
            ALU_EQ : begin
                fu.resp_done <= 1;
                fu.resp_result <= (reg_req_op1 == reg_req_op2) ? SIGNED_ONE : MIN_CLAMP;
            end
            ALU_NE : begin
                fu.resp_done <= 1;
                fu.resp_result <= (reg_req_op1 == reg_req_op2) ? MIN_CLAMP : SIGNED_ONE;
            end
            ALU_LT : begin
                fu.resp_done <= 1;
                fu.resp_result <= (reg_req_op1 < reg_req_op2) ? SIGNED_ONE : MIN_CLAMP;
            end
            ALU_GE : begin
                fu.resp_done <= 1;
                fu.resp_result <= (reg_req_op1 < reg_req_op2) ? MIN_CLAMP : SIGNED_ONE;
            end
            default: begin
                fu.resp_done <= 0;
                fu.resp_result <= 0;
            end
        endcase
    end else begin
        fu.resp_done <= 0;
        fu.resp_result <= 0;    
    end
end

assign fu.req_ready = (!rst_n) ? 0 : 1;
assign sum = reg_req_op1 + reg_req_op2;
assign diff = reg_req_op1 - reg_req_op2;

endmodule
