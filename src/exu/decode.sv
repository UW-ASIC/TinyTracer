`default_nettype wire

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
        logic vector;
        logic [5:0] start_addr;
        logic [5:0] end_addr;
    } macro_decode_t;

    macro_decode_t macro_decode;

    // Yosys cannot select struct fields through an interface, so copy it out
    tinytracer_pkg::macro_word_t macro_req_op;
    assign macro_req_op = macro.req_op;

    always @(*) begin // for DECODE & DISPATCH
        macro_decode = '0;
        case (macro_req_op.op) // check only the opcode of macro.req_op
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

    //from tinytracer_pkg:
    tinytracer_pkg::fmt_t        fmt_reg;
    tinytracer_pkg::micro_word_t micro_op_word; // 13b micro op structure

    // Instantitate rom
    micro_op_rom m_op_rom (
        .addr (curr_addr),
        .micro_op_word (micro_op_word),
        .barrier (barrier)
    );
    logic       macro_accept; // for handshake confirmation?
    logic       micro_issue;
    logic       vector_macro;

    // STATE_DISPATCH
    logic stall;
    logic vector_done;
    logic scalar_done;



    // RESET LOGIC

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= STATE_DECODE; // let decode be the reset state
            fmt_reg <= tinytracer_pkg::FMT_POS;
            inflight <= 4'd0;
            vector_macro <= 1'b0;
            curr_addr <= 6'd0;
            op_addr_end <= 6'd0;

        end

        else begin // sequential updates
            state <= next_state;
            inflight <= inflight + 4'(micro_issue) - 4'(micro.resp_done); // current outstanding + #issed - #completed

            if (macro_accept) begin // update request-specific registers only on acceptance
                fmt_reg      <= macro_req_op.fmt;
                vector_macro <= macro_decode.vector; // is op a vec/scalar?

                if (macro_decode.vector) begin
                    curr_addr   <= macro_decode.start_addr;
                    op_addr_end <= macro_decode.end_addr;
                end
            end

            else if (state == STATE_DISPATCH && micro_issue) begin
                curr_addr <= curr_addr + 6'd1;
            end
        end
    end

    // STATE LOGIC
    // Decode acts like a server for macro ops, recieve work from upstream
    // Decode acts like a client for micro ops, send work to the FU

    always @(*) begin
        next_state = state; // stay in curr state

        // macro.if.server
        macro.req_ready = 1'b0; // accept macro op only in DECODE
        macro.resp_valid = 1'b0;
        macro.resp_result = rf_result; // keeping it driven cts.

        // micro.if.client
        micro.req_valid = 1'b0; // 0 unless dispatch/scalar issues it
        micro.req_op = '0;
        micro.req_fmt = fmt_reg;
        micro.req_direct = 1'b0;
        micro.req_u1 = '0;
        micro.req_v1 = '0;

        // register file
        rf_load = 1'b0;

        macro_accept = 1'b0;
        micro_issue = 1'b0;

        vector_done = 1'b0;
        scalar_done = 1'b0;

        case (state)
            STATE_DECODE: begin
                // assert rf_load, set macro.req_ready =1
                // load into register file reg_file.sv. Load MACROOP and FMT into register
                // check is op vec/scalar
                // VECTOR: set curr_addr to the first op row, op_addr_end to last op row
                // SCALAR: issue single micro op to FU ctrl right away, micro opcode = MACROOP[3:0], result go to R0, u,v taken from micro.req_direct=1
                // set next stateback to dispatch

                macro.req_ready = 1'b1;

                if (!macro_decode.vector && macro.req_valid) begin // for scalar op, assign registers and break macro into micro ops
                    micro.req_valid = 1'b1;
                    micro_issue = micro.req_valid && micro.req_ready; // increments inflight
                    micro.req_direct = 1'b1;
                    micro.req_fmt = macro_req_op.fmt; // fmt_reg is not loaded until the end of this cycle
                    micro.req_u1 = macro_req_op.u.x;
                    micro.req_v1 = macro_req_op.v.x;
                    micro.req_op = {3'd0, 3'd0, 3'd0, macro_req_op.op[3:0]}; // rs1, rs2 are don't cares, scalar result goes to r0=0
                end
                macro_accept = macro.req_valid && macro.req_ready; // handshake complete - RTU send valid macro, DECODE accepted it

                if (macro_accept) begin
                    rf_load = 1'b1; // assert rf load in the cycle a macro-op is accepted
                    next_state = STATE_DISPATCH;
                end
            end

            STATE_DISPATCH: begin

                micro.req_valid = (curr_addr != op_addr_end) && (!barrier || inflight == 0);
                micro.req_op    = micro_op_word; // micro_op_word is determined by ROM

                // Issue when request is valid and request is ready
                micro_issue = micro.req_valid && micro.req_ready;

                stall = (inflight != 0 && (curr_addr == op_addr_end || barrier)) || (curr_addr != op_addr_end && !micro.req_ready);

                vector_done = (curr_addr == op_addr_end) && (inflight == 0);
                scalar_done = !vector_macro && micro.resp_done;

                if (vector_done || scalar_done) begin
                    next_state = STATE_WRITEBACK;
                end
            end
            STATE_WRITEBACK: begin

                macro.resp_valid = 1'b1; // set our response to be valid

                if (macro.resp_ready) begin // waiting until the response is done
                    next_state = STATE_DECODE;
                end
            end

            default:
                // Default to the decode state, should not arrive here
                next_state = STATE_DECODE;

        endcase
    end

    // CTRL registers
    // macro_op FMT, curr addr, ROM end addr, inflight count

    // handshake logic
    // macro req, micro issue, micro complete, macro response

endmodule
