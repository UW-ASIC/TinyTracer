
`default_nettype wire

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
            // ADD R0 <- R0, R3
            // w1 = u1 + v1.
            6'd0: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd0;
                micro_op_word.rs1 = 3'd0;
                micro_op_word.rs2 = 3'd3;
            end

            // ADD R1 <- R1, R4
            // w2 = u2 + v2.
            6'd1: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd1;
                micro_op_word.rs1 = 3'd1;
                micro_op_word.rs2 = 3'd4;
            end

            // ADD R2 <- R2, R5
            // w3 = u3 + v3.
            6'd2: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd2;
                micro_op_word.rs1 = 3'd2;
                micro_op_word.rs2 = 3'd5;
            end

            // M_VSUB
            // SUB R0 <- R0, R3
            // w1 = u1 - v1.
            6'd3: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd0;
                micro_op_word.rs1 = 3'd0;
                micro_op_word.rs2 = 3'd3;
                micro_op_word.op = tinytracer_pkg::U_SUB;
            end

            // SUB R1 <- R1, R4
            // w2 = u2 - v2.
            6'd4: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd1;
                micro_op_word.rs1 = 3'd1;
                micro_op_word.rs2 = 3'd4;
                micro_op_word.op = tinytracer_pkg::U_SUB;
            end

            // SUB R2 <- R2, R5
            // w3 = u3 - v3.
            6'd5: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd2;
                micro_op_word.rs1 = 3'd2;
                micro_op_word.rs2 = 3'd5;
                micro_op_word.op = tinytracer_pkg::U_SUB;
            end

            // M_SCAL_VEC
            // MUL R1 <- R0, R4
            // w2 = u1 * v2; keep the scalar in R0 for the remaining products.
            6'd6: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd1;
                micro_op_word.rs1 = 3'd0;
                micro_op_word.rs2 = 3'd4;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // MUL R2 <- R0, R5
            // w3 = u1 * v3; keep the scalar in R0 for the final product.
            6'd7: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd2;
                micro_op_word.rs1 = 3'd0;
                micro_op_word.rs2 = 3'd5;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // MUL R0 <- R0, R3
            // w1 = u1 * v1; issued last because it overwrites the scalar.
            6'd8: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd0;
                micro_op_word.rs1 = 3'd0;
                micro_op_word.rs2 = 3'd3;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // M_DOT
            // MUL R0 <- R0, R3
            // Compute the first dot-product term, u1 * v1.
            6'd9: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd0;
                micro_op_word.rs1 = 3'd0;
                micro_op_word.rs2 = 3'd3;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // MUL R1 <- R1, R4
            // Compute the second dot-product term, u2 * v2.
            6'd10: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd1;
                micro_op_word.rs1 = 3'd1;
                micro_op_word.rs2 = 3'd4;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // MUL R2 <- R2, R5
            // Compute the third dot-product term, u3 * v3.
            6'd11: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd2;
                micro_op_word.rs1 = 3'd2;
                micro_op_word.rs2 = 3'd5;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // ADD R0 <- R0, R1
            // Add u1 * v1 + u2 * v2; barrier waits for the products.
            6'd12: begin
                barrier =           1'b1;
                micro_op_word.rd =  3'd0;
                micro_op_word.rs1 = 3'd0;
                micro_op_word.rs2 = 3'd1;
                micro_op_word.op = tinytracer_pkg::U_ADD;
            end

            // ADD R0 <- R0, R2
            // Add u3 * v3 to finish the dot product; barrier waits for the partial sum.
            6'd13: begin
                barrier =           1'b1;
                micro_op_word.rd =  3'd0;
                micro_op_word.rs1 = 3'd0;
                micro_op_word.rs2 = 3'd2;
                micro_op_word.op = tinytracer_pkg::U_ADD;
            end

            // M_CROSS
            // MUL R6 <- R2, R4
            // Save u3 * v2 in R6 for the first cross-product component.
            6'd14: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd6;
                micro_op_word.rs1 = 3'd2;
                micro_op_word.rs2 = 3'd4;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // MUL R2 <- R2, R3
            // Compute u3 * v1 for the second cross-product component.
            6'd15: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd2;
                micro_op_word.rs1 = 3'd2;
                micro_op_word.rs2 = 3'd3;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // MUL R4 <- R0, R4
            // Compute u1 * v2 for the third cross-product component.
            6'd16: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd4;
                micro_op_word.rs1 = 3'd0;
                micro_op_word.rs2 = 3'd4;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // MUL R3 <- R1, R3
            // Compute u2 * v1 for the third cross-product component.
            6'd17: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd3;
                micro_op_word.rs1 = 3'd1;
                micro_op_word.rs2 = 3'd3;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // MUL R1 <- R1, R5
            // Compute u2 * v3 for the first cross-product component.
            6'd18: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd1;
                micro_op_word.rs1 = 3'd1;
                micro_op_word.rs2 = 3'd5;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // MUL R5 <- R0, R5
            // Compute u1 * v3 for the second cross-product component.
            6'd19: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd5;
                micro_op_word.rs1 = 3'd0;
                micro_op_word.rs2 = 3'd5;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // SUB R0 <- R1, R6
            // w1 = u2 * v3 - u3 * v2; barrier waits for all products.
            6'd20: begin
                barrier =           1'b1;
                micro_op_word.rd =  3'd0;
                micro_op_word.rs1 = 3'd1;
                micro_op_word.rs2 = 3'd6;
                micro_op_word.op = tinytracer_pkg::U_SUB;
            end

            // SUB R1 <- R2, R5
            // w2 = u3 * v1 - u1 * v3.
            6'd21: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd1;
                micro_op_word.rs1 = 3'd2;
                micro_op_word.rs2 = 3'd5;
                micro_op_word.op = tinytracer_pkg::U_SUB;
            end

            // SUB R2 <- R4, R3
            // w3 = u1 * v2 - u2 * v1.
            6'd22: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd2;
                micro_op_word.rs1 = 3'd4;
                micro_op_word.rs2 = 3'd3;
                micro_op_word.op = tinytracer_pkg::U_SUB;
            end

            // M_NORM
            // MAG R4 <- R0, R1
            // Compute sqrt(u1^2 + u2^2), the magnitude of the first two components.
            6'd23: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd4;
                micro_op_word.rs1 = 3'd0;
                micro_op_word.rs2 = 3'd1;
                micro_op_word.op = tinytracer_pkg::U_MAG;
            end

            // MAG R4 <- R4, R2
            // Compute |u| = sqrt(u1^2 + u2^2 + u3^2); barrier waits for the first MAG.
            6'd24: begin
                barrier =           1'b1;
                micro_op_word.rd =  3'd4;
                micro_op_word.rs1 = 3'd4;
                micro_op_word.rs2 = 3'd2;
                micro_op_word.op = tinytracer_pkg::U_MAG;
            end

            // DIV R4 <- R3, R4
            // Compute 1 / |u| using the DIR constant in R3; barrier waits for |u|.
            6'd25: begin
                barrier =           1'b1;
                micro_op_word.rd =  3'd4;
                micro_op_word.rs1 = 3'd3;
                micro_op_word.rs2 = 3'd4;
                micro_op_word.op = tinytracer_pkg::U_DIV;
            end

            // MUL R0 <- R4, R0
            // w1 = u1 / |u|; barrier waits for the reciprocal.
            6'd26: begin
                barrier =           1'b1;
                micro_op_word.rd =  3'd0;
                micro_op_word.rs1 = 3'd4;
                micro_op_word.rs2 = 3'd0;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // MUL R1 <- R4, R1
            // w2 = u2 / |u| using the reciprocal in R4.
            6'd27: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd1;
                micro_op_word.rs1 = 3'd4;
                micro_op_word.rs2 = 3'd1;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // MUL R2 <- R4, R2
            // w3 = u3 / |u| using the reciprocal in R4.
            6'd28: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd2;
                micro_op_word.rs1 = 3'd4;
                micro_op_word.rs2 = 3'd2;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // M_SPHERE_NORM
            // DIV R1 <- R4, R0
            // w2 = v2 / radius; preserve the radius in R0.
            6'd29: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd1;
                micro_op_word.rs1 = 3'd4;
                micro_op_word.rs2 = 3'd0;
                micro_op_word.op = tinytracer_pkg::U_DIV;
            end

            // DIV R2 <- R5, R0
            // w3 = v3 / radius; preserve the radius in R0.
            6'd30: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd2;
                micro_op_word.rs1 = 3'd5;
                micro_op_word.rs2 = 3'd0;
                micro_op_word.op = tinytracer_pkg::U_DIV;
            end

            // DIV R0 <- R3, R0
            // w1 = v1 / radius; issued last because it overwrites the radius.
            6'd31: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd0;
                micro_op_word.rs1 = 3'd3;
                micro_op_word.rs2 = 3'd0;
                micro_op_word.op = tinytracer_pkg::U_DIV;
            end

            // M_VMUL
            // MUL R0 <- R0, R3
            // w1 = u1 * v1, the first element-wise product.
            6'd32: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd0;
                micro_op_word.rs1 = 3'd0;
                micro_op_word.rs2 = 3'd3;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // MUL R1 <- R1, R4
            // w2 = u2 * v2, the second element-wise product.
            6'd33: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd1;
                micro_op_word.rs1 = 3'd1;
                micro_op_word.rs2 = 3'd4;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // MUL R2 <- R2, R5
            // w3 = u3 * v3, the third element-wise product.
            6'd34: begin
                barrier =           1'b0;
                micro_op_word.rd =  3'd2;
                micro_op_word.rs1 = 3'd2;
                micro_op_word.rs2 = 3'd5;
                micro_op_word.op = tinytracer_pkg::U_MUL;
            end

            // Unused addresses retain the default zero word
            default: begin
            end
        endcase
    end

endmodule
