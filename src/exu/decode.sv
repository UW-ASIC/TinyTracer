`default_nettype wire

import tinytracer_pkg::macro_op_t;

module decode (
    input  logic        clk,
    input  logic        rst_n,

    // RTU <-> Decode Interface (passed through by the EXU)
    macro_if.server     macro,

    // Decode <-> FU Interface
    micro_if.client     micro,

    // Register File Ports: rf_load loads the macro-op operands in the cycle
    // the macro-op is accepted; rf_result drives the macro-op result.
    output logic                   rf_load,
    input  tinytracer_pkg::vec3_t  rf_result
);

    typedef struct packed {
        logic [5:0] start_addr;
        logic [5:0] end_addr;
    } rom_addr_t;

    typedef struct packed {
        logic vector;
        logic [5:0] start_addr;
        logic [5:0] end_addr;
    } macro_decode_t;

    macro_decode_t macro_decode;

    always @(*) begin 
        macro_decode = '0;
        case (macro.req_op)
            tinytracer_pkg::M_VADD: begin 
                macro_decode.vector = 1'b1;
                macro_decode.start_addr = 6'd0;
                macro_decode.end_addr = 6'd3;
            end
            tinytracer_pkg::M_VSUB: begin 
                macro_decode.vector = 1'b1;
                macro_decode.start_addr = 6'd3;
                macro_decode.end_addr = 6'd6;
            end
            tinytracer_pkg::M_SCAL_VEC: begin 
                macro_decode.vector = 1'b1;
                macro_decode.start_addr = 6'd6;
                macro_decode.end_addr = 6'd9;
            end
            tinytracer_pkg::M_DOT: begin
                macro_decode.vector = 1'b1;
                macro_decode.start_addr = 6'd9;
                macro_decode.end_addr = 6'd14;
            end
            tinytracer_pkg::M_CROSS: begin 
                macro_decode.vector = 1'b1;
                macro_decode.start_addr = 6'd14;
                macro_decode.end_addr = 6'd23;
            end
            tinytracer_pkg::M_NORM: begin 
                macro_decode.vector = 1'b1;
                macro_decode.start_addr = 6'd23;
                macro_decode.end_addr = 6'd29;
           end
           tinytracer_pkg::M_SPHERE_NORM: begin 
                macro_decode.vector = 1'b1;
                macro_decode.start_addr = 6'd29;
                macro_decode.end_addr = 6'd32;
           end
           tinytracer_pkg::M_VMUL: begin 
                macro_decode.vector = 1'b1;
                macro_decode.start_addr = 6'd32;
                macro_decode.end_addr = 6'd35;
           end
            default: begin 
                macro_decode.vector = 1'b0;
                macro_decode.start_addr = 6'd0;
                macro_decode.end_addr = 6'd0;
            end
        endcase
    end

    // 3 states
    // DECODE -> DISPATCH -> WB
    localparam logic [1:0] STATE_DECODE = 2'b00;
    localparam logic [1:0] STATE_DISPATCH = 2'b01;
    localparam logic [1:0] STATE_WRITEBACK = 2'b10;

    logic [1:0] state;
    logic [1:0] next_state;

    logic [5:0] curr_addr; // address for ROM
    logic [5:0] op_addr_end;
    logic [3:0] inflight; //4b counter
    logic barrier;

    logic [5:0] rom_addr_start; // ROM addr start for macro op insn
    logic [5:0] rom_addr_end; // ROM addr end for macro op insn

    logic       macro_accept; // for handshake confirmation?
    logic       micro_issue;
    logic       vector_macro;

    //from tinytracer_pkg:
    macro_op_t   macroop_reg; // 5b macro opcode
    tinytracer_pkg::fmt_t        fmt_reg;
    tinytracer_pkg::micro_word_t micro_op_word; // 13b micro op structure

    // RESET LOGIC

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= STATE_DECODE; // let decode be the reset state
            macroop_reg <= '0;
            fmt_reg <= '0;
            vector_macro <= 1'b0;
            curr_addr <= 6'd0;
            op_addr_end <= 6'd0;
            inflight <= 4'd0;
        end
        else begin
            state <= next_state;
            macroop_reg <= macro.req_op;
            fmt_reg <= macro.fmt_reg;
            vector_macro <= macro_decode.vector;
            curr_addr <= macro_decode.start_addr;
            op_addr_end <= macro_decode.end_addr;
        end
    end

    // STATE LOGIC

    always @(*) begin
        next_state = state;

        macro.req_ready = 1'b0; // ready to accept macrop only in decode
        macro.resp_valid = 1'b0;
        micro.req_ready = 1'b0;
        micro.req_direct = 1'b0;
        rf_load = 1'b0;

        case (state)
            STATE_DECODE: begin
                // assert rf_load, set macro.req_ready =1
                // load into register file reg_file.sv. Load MACROOP and FMT into register
                // is op vec/scalar? - write a function for this
                // VECTOR: set curr_addr to the first op row, op_addr_end to last op row
                // SCALAR: issue single micro op to FU ctrl right away, micro opcode = MACROOP[3:0], result go to R0, u,v taken from micro.req_direct=1
                // set next stateback to dispatch (if vector), writback (if scalar)

                macro.req_ready = 1'b1;
                macro_accept = macro.req_valid && macro.req_ready; // handshake complete - RTU send valid macro, DECODE accepted it

                if (macro_accept) begin
                    rf_load = 1'b1; // reg_file.sv for the loading logic
                    next_state = STATE_DISPATCH; // we accepted macro op, move to next state
                end

                if (vector_macro) begin 

                end

                




            end
            STATE_DISPATCH: begin

            end
            STATE_WRITEBACK: begin

            end

        endcase
    end


    // CTRL registers
    // macro_op FMT, curr addr, ROM end addr, inflight count

    // ROM and ROM lookup
    function automatic rom_addr_t get_rom_range(
        input tinytracer_pkg::macro_op_t op
    );
        case (op)
            tinytracer_pkg::M_VADD:
                get_rom_range = '{6'd0, 6'd3}; // assign into the struct with '
            // missing more function
            default:
                get_rom_range = '{6'd0, 6'd0};
        endcase
    endfunction

    always_comb begin
        barrier = 1'b0;
        micro_op_word = '0;

        case (curr_addr)

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

    // handshake logic
    // macro req, micro issue, micro complete, macro response

endmodule
