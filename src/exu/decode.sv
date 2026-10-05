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


    // 3 states
    // DECODE -> DISPATCH -> WB
    localparam logic [1:0] STATE_DECODE = 2'b00;
    localparam logic [1:0] STATE_DISPATCH = 2'b01;
    localparam logic [1:0] STATE_WRITEBACK = 2'b10;

    logic [1:0] state;
    logic [1:0] next_state;

    logic [5:0] curr_addr;
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
    fmt_t        fmt_reg;
    micro_word_t micro_op_word; // 13b micro op structure

    // RESET LOGIC

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= STATE_DECODE; // let decode be the reset state
        end
        else begin
            state <= next_state;
        end
    end

    // STATE LOGIC

    always @(*) begin
        next_state = state;
        case (state)
            STATE_DECODE: begin
                // assert rf_load, set macro.req_ready =1
                // load into register file reg_file.sv. Load MACROOP and FMT into register
                // is op vec/scalar? - write a function for this
                // VECTOR: set curr_addr to the first op row, op_addr_end to last op row
                // SCALAR: issue single micro op to FU ctrl right away, micro opcode = MACROOP[3:0], result go to R0, u,v taken from micro.req_direct=1
                // set next stateback to dispatch (if vector), writback (if scalar)

                macro.req_ready = 1'b1;

                if (macro_accept) begin
                    rf_load = 1'b1; // reg_file.sv for loading logic
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

    // ROM lookup
    //
    function automatic rom_range_t get_rom_range(
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

    // handshake logic
    // macro req, micro issue, micro complete, macro response

endmodule
