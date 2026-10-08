
`default_nettype wire

import tinytracer_pkg::macro_op_t;

module micro_op_rom (
    input logic [5:0] addr,
    output tinytracer_pkg::micro_word_t micro_op_word,
    output logic barrier
);

    always_comb begin
        barrier = 1'b0;
        micro_op_word = '0;

        case (addr)

            // M_VADD
            6'd0: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd0;
                micro_op_word.rs1 = 3'd0;
                micro_op_word.rs2 = 3'd3;
            end

            6'd1: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd1;
                micro_op_word.rs1 = 3'd1;
                micro_op_word.rs2 = 3'd4;
            end

            6'd2: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd2;
                micro_op_word.rs1 = 3'd2;
                micro_op_word.rs2 = 3'd5;
            end

            // Default case do nothing
            default: begin
            end
        endcase
    end

endmodule
