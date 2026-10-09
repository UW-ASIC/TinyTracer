`default_nettype wire

module fu_control (
    input logic clk,
    input logic rst_n,

    // Register File Ports (both read ports for operands, write port for results)
    output logic                            rf_wen,
    output logic [                     2:0] rf_waddr,
    output logic [tinytracer_pkg::WLEN-1:0] rf_wdata,
    output logic [                     2:0] rf_raddr1,
    input  logic [tinytracer_pkg::WLEN-1:0] rf_rdata1,
    output logic [                     2:0] rf_raddr2,
    input  logic [tinytracer_pkg::WLEN-1:0] rf_rdata2,

    // Micro-op Channel (scalar macro-ops carry their operands on it instead
    // of using the read ports)
    micro_if.server micro
);

  // FU Control <-> Functional Units
  fu_if fu_alu ();
  fu_if fu_mul ();
  fu_if fu_cordic ();

  alu u_alu (
      .clk  (clk),
      .rst_n(rst_n),
      .fu   (fu_alu)
  );

  multiplier u_multiplier (
      .clk  (clk),
      .rst_n(rst_n),
      .fu   (fu_mul)
  );

  cordic u_cordic (
      .clk  (clk),
      .rst_n(rst_n),
      .fu   (fu_cordic)
  );

  logic [2:0] rd;
  logic [2:0] rs1;
  logic [2:0] rs2;
  tinytracer_pkg::micro_op_t op;

  logic [15:0] operand1;
  logic [15:0] operand2;

  tinytracer_pkg::fu_sel_t unit_sel;
  logic [2:0] fu_opcode;
  logic accept;

  logic [2:0] alu_rd;
  logic [2:0] mul_rd;
  logic [2:0] cordic_rd;

  logic [15:0] data;
  logic [2:0] address;


  assign rd = micro.req_op[12:10];
  assign rs1 = micro.req_op[9:7];
  assign rs2 = micro.req_op[6:4];
  assign op = micro.req_op[3:0];

  assign rf_raddr1 = rs1;
  assign rf_raddr2 = rs2;

  assign operand1 = (micro.req_direct) ? micro.req_u1 : rf_rdata1;
  assign operand2 = (micro.req_direct) ? micro.req_v1 : rf_rdata2;

  always_comb begin
    unit_sel  = tinytracer_pkg::FU_ALU;
    fu_opcode = '0;

    case (op)
      tinytracer_pkg::U_MUL: begin
        unit_sel = tinytracer_pkg::FU_MUL;
      end
      tinytracer_pkg::U_ADD: begin
        unit_sel  = tinytracer_pkg::FU_ALU;
        fu_opcode = tinytracer_pkg::ALU_ADD;
      end
      tinytracer_pkg::U_SUB: begin
        unit_sel  = tinytracer_pkg::FU_ALU;
        fu_opcode = tinytracer_pkg::ALU_SUB;
      end
      tinytracer_pkg::U_EQ: begin
        unit_sel  = tinytracer_pkg::FU_ALU;
        fu_opcode = tinytracer_pkg::ALU_EQ;
      end
      tinytracer_pkg::U_NE: begin
        unit_sel  = tinytracer_pkg::FU_ALU;
        fu_opcode = tinytracer_pkg::ALU_NE;
      end
      tinytracer_pkg::U_LT: begin
        unit_sel  = tinytracer_pkg::FU_ALU;
        fu_opcode = tinytracer_pkg::ALU_LT;
      end
      tinytracer_pkg::U_GE: begin
        unit_sel  = tinytracer_pkg::FU_ALU;
        fu_opcode = tinytracer_pkg::ALU_GE;
      end
      tinytracer_pkg::U_DIV: begin
        unit_sel  = tinytracer_pkg::FU_CORDIC;
        fu_opcode = 3'(tinytracer_pkg::CORDIC_DIV);
      end
      tinytracer_pkg::U_SQRT: begin
        unit_sel  = tinytracer_pkg::FU_CORDIC;
        fu_opcode = 3'(tinytracer_pkg::CORDIC_SQRT);
      end
      tinytracer_pkg::U_COS: begin
        unit_sel  = tinytracer_pkg::FU_CORDIC;
        fu_opcode = 3'(tinytracer_pkg::CORDIC_COS);
      end
      tinytracer_pkg::U_MAG: begin
        unit_sel  = tinytracer_pkg::FU_CORDIC;
        fu_opcode = 3'(tinytracer_pkg::CORDIC_MAG);
      end
      default: begin
      end

    endcase
  end

  always_comb begin
    micro.req_ready = '0;
    case(unit_sel)
      tinytracer_pkg::FU_ALU: begin
        micro.req_ready = fu_alu.req_ready;
      end
      tinytracer_pkg::FU_MUL: begin
        micro.req_ready = fu_mul.req_ready;
      end
      tinytracer_pkg::FU_CORDIC: begin
        micro.req_ready = fu_cordic.req_ready;
      end
      default: begin
      end
    endcase
  end

  always_comb begin
    accept = micro.req_ready & micro.req_valid;

    fu_alu.req_valid = accept & (unit_sel == tinytracer_pkg::FU_ALU);
    fu_mul.req_valid = accept & (unit_sel == tinytracer_pkg::FU_MUL);
    fu_cordic.req_valid = accept & (unit_sel == tinytracer_pkg::FU_CORDIC);

    fu_alu.req_op1 = operand1;
    fu_alu.req_op2 = operand2;
    fu_mul.req_op1 = operand1;
    fu_mul.req_op2 = operand2;
    fu_cordic.req_op1 = operand1;
    fu_cordic.req_op2 = operand2;

    fu_alu.req_opcode = fu_opcode;
    fu_mul.req_opcode = fu_opcode;
    fu_cordic.req_opcode = fu_opcode;

    fu_alu.req_fmt = micro.req_fmt;
    fu_mul.req_fmt = micro.req_fmt;
    fu_cordic.req_fmt = micro.req_fmt;

  end


  always_ff @(posedge clk) begin
    if (!rst_n) begin
      alu_rd <= '0;
      mul_rd <= '0;
      cordic_rd <= '0;
    end else begin
      alu_rd <= (fu_alu.req_valid) ? rd : alu_rd;
      mul_rd <= (fu_mul.req_valid) ? rd : mul_rd;
      cordic_rd <= (fu_cordic.req_valid) ? rd : cordic_rd;
    end

  end

  always_comb begin 
    rf_wen = 1'b0;
    data = '0;
    address = '0;

    if (fu_alu.resp_done) begin 
      data = fu_alu.resp_result;
      address = alu_rd;

      rf_wen = 1'b1;
    end
    else if (fu_mul.resp_done) begin
      data = fu_mul.resp_result;
      address = mul_rd;

      rf_wen = 1'b1;
    end
    else if (fu_cordic.resp_done) begin
      data = fu_cordic.resp_result;
      address = cordic_rd;

      rf_wen = 1'b1;
    end

    rf_waddr = address;
    rf_wdata = data;

    micro.resp_done = rf_wen;
  end



endmodule
