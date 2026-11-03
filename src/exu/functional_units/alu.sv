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

// local registers
logic reg_req_valid;
logic signed [WLEN-1:0] reg_req_op1;
logic signed [WLEN-1:0] reg_req_op2;
logic [2:0] reg_req_opcode;

// local wires
logic sub_en;
logic signed [WLEN-1:0] t_reg_req_op2;
logic signed [WLEN-1:0] raw_res;
logic add_overflow;

// local parameters
localparam signed [WLEN-1:0] MAX_CLAMP = {1'b0, {WLEN-1{1'b1}}};
localparam signed [WLEN-1:0] MIN_CLAMP = {1'b1, {WLEN-1{1'b0}}};
localparam signed [WLEN-1:0] SIGNED_ONE = {{(WLEN-1){1'b0}}, 1'b1};

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
    // compute sub_en
    sub_en = (reg_req_opcode != ALU_ADD) ? 1'b1 : 1'b0; 

    // toggle req_op2 bits for non-addition operations
    t_reg_req_op2 = (sub_en) ? (~reg_req_op2 + WLEN_ONE) : reg_req_op2;

    // 16-bit adder
    raw_res = reg_req_op1 + t_reg_req_op2;

    // detect overflow
    add_overflow = (reg_req_op1[15] == reg_req_op2[15]) && (reg_req_op1[15] != raw_res[15]) ? 1'b1 : 1'b0;

    case (reg_req_opcode)
        // 1) saturation logic
        3'b000, 3'b001: fu.resp_result = add_overflow ? (reg_req_op1[15]) ? MAX_CLAMP : MIN_CLAMP : raw_res;

        // 2) compare logic
        3'b010 : fu.resp_result = (raw_res) ? SIGNED_ONE : MIN_CLAMP;
        3'b011 : fu.resp_result = (!raw_res) ? SIGNED_ONE : MIN_CLAMP ;
        3'b100 : fu.resp_result = (add_overflow ^ raw_res[15]) ? SIGNED_ONE : MIN_CLAMP;
        3'b101 : fu.resp_result = !(add_overflow ^ raw_res[15]) ? SIGNED_ONE : MIN_CLAMP;
        default : fu.resp_result = MIN_CLAMP;
    endcase
end

assign fu.req_ready = !rst_n;
assign fu.resp_done = reg_req_valid;

endmodule