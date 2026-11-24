`default_nettype wire
module alu #(
    parameter WLEN = tinytracer_pkg::WLEN
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
        reg_req_valid   <= '0;
        reg_req_op1     <= '0;
        reg_req_op2     <= '0;
        reg_req_opcode  <= '0;
    end else begin
        reg_req_valid   <= fu.req_valid;
        reg_req_op1     <= fu.req_op1;
        reg_req_op2     <= fu.req_op2;
        reg_req_opcode  <= fu.req_opcode;
    end
end

always_comb begin
    // compute sub_en
    sub_en = (reg_req_opcode != tinytracer_pkg::ALU_ADD);

    // conditional bit inversion
    t_reg_req_op2 = reg_req_op2 ^ {WLEN{sub_en}};

    // 16-bit adder
    raw_res = reg_req_op1 + t_reg_req_op2;
    raw_res = (sub_en) ? (raw_res + SIGNED_ONE) : raw_res;

    // detect overflow
    add_overflow =
        (reg_req_op1[WLEN-1] == t_reg_req_op2[WLEN-1]) &&
        (reg_req_op1[WLEN-1] != raw_res[WLEN-1]);

    case (reg_req_opcode)
        // 1) saturation logic
        tinytracer_pkg::ALU_ADD, tinytracer_pkg::ALU_SUB: fu.resp_result = add_overflow ? (reg_req_op1[WLEN-1] ? MIN_CLAMP : MAX_CLAMP) : raw_res;

        // 2) compare logic
        tinytracer_pkg::ALU_EQ : fu.resp_result = (!raw_res) ? SIGNED_ONE : '0 ;
        tinytracer_pkg::ALU_NE : fu.resp_result = (raw_res) ? SIGNED_ONE : '0;
        tinytracer_pkg::ALU_LT : fu.resp_result = (add_overflow ^ raw_res[WLEN-1]) ? SIGNED_ONE : '0;
        tinytracer_pkg::ALU_GE : fu.resp_result = !(add_overflow ^ raw_res[WLEN-1]) ? SIGNED_ONE : '0;
        default : fu.resp_result = '0;
    endcase
end

assign fu.req_ready = rst_n;
assign fu.resp_done = reg_req_valid;

endmodule