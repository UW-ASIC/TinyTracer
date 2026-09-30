`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

// Intersection Unit: finds the closest thing that one ray segment hits.
module intersection_unit #(
    parameter ADDR_WIDTH = 9,
    parameter WLEN       = 16,
    parameter DATA_WIDTH = 16
) (
    input  logic                   clk,
    input  logic                   rst_n,       // global reset, active low

    // RTU FSM <-> Intersection Unit
    input  logic                   start,       // 1-cycle pulse: search one segment
    output logic                   done,        // 1-cycle pulse: the hit outputs are valid
    output logic                   hit,         // 1 = object or ground hit, 0 = sky
    output logic                   hit_ground,  // 1 = the hit is the ground (only with hit = 1)
    output logic [WLEN-1:0]        hit_t,       // distance to the hit, POS (Q9.7)
    output logic [ADDR_WIDTH-1:0]  hit_addr,    // SRAM address of the hit object's w0
    output logic                   hit_flip,    // sphere: ray started inside; triangle: back side

    // Ray and scene, from RTU registers (must not change from start to done)
    input  logic [47:0]            ray_origin,  // O, POS (Q9.7): z [47:32], y [31:16], x [15:0]
    input  logic [47:0]            ray_dir,     // D, DIR (Q2.14), length 1: z [47:32], y [31:16], x [15:0]
    input  logic [4:0]             bv_count,    // number of BVs, 0 to 16 (header w15[7:3])

    // SRAM reads (the RTU passes them on to the SRAM Controller)
    output logic [ADDR_WIDTH-1:0]  sram_addr,   // register: address of the word to read
    output logic                   sram_rd,     // 1-cycle pulse: read the word at sram_addr
    input  logic [DATA_WIDTH-1:0]  sram_data,   // SRAM word, shared by all RTU sub-blocks
    input  logic                   sram_valid,  // 1 = sram_data holds the word asked for

    // Macro-ops (the RTU passes them on to the Decode Unit; the macro_if client signals)
    output logic                   req_valid,   // 1 = req_op holds a macro-op
    output logic [101:0]           req_op,      // fmt [101], u [100:53], v [52:5], opcode [4:0]
    input  logic                   req_ready,   // 1 = the Decode Unit takes req_op in this cycle
    input  logic                   resp_valid,  // 1 = resp_result holds the result
    input  logic [3*WLEN-1:0]      resp_result, // z [47:32], y [31:16], x [15:0]; a compare gives 1 or 0 in x
    output logic                   resp_ready   // 1 = the IU takes resp_result in this cycle
);

    // Assumption:
    // input ray_origin, ray_dir, bv_count stay same in between start 1-cycle pulse
    // input resp_valid, resp_result stay same until resp_ready and req_valid(?)

    // FSM States
    typedef enum logic [2:0] {
        S_IDLE       = 3'd0,
        S_RTU_LOAD   = 3'd1,
        S_SRAM_READ  = 3'd2,
        S_DECODE     = 3'd3,
        S_CAL        = 3'd4
    } state_t;

    state_t state_q, state_d;

    // Next-State Combinational Logic
    always_comb begin
        state_d = state_q;
        case (state_q)
            S_IDLE: begin
                if (start) state_d = S_RTU_LOAD;
            end
            S_RTU_LOAD: begin
                if (bv_count==0) state_d = S_DECODE;
                else state_d = S_SRAM_READ;
            end
            S_SRAM_READ: begin
                if (sram_bv_done) state_d = S_DECODE;
            end
            S_DECODE: begin
                if (resp_valid) state_d = S_CAL;
            end
            S_CAL: begin
                // if (cal_done) state_d = S_IDLE;
            end

            default: state_d = S_IDLE;
        endcase
    end

    // Internal tracking
    logic [4:0]  bv_index;
    logic [2:0]  sram_w_index; // BV Address: w0-w4
    logic        sram_bv_done;

    // FSM Sequential Iteration
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state_q       <= S_IDLE;
            bv_index      <= 5'd0;
            sram_addr     <= 9'd17; // BV Address = 17 + 5 * i + word
            sram_w_index  <= 3'd0; // BV Address: w0-w4
            sram_rd       <= 1'b0; 
            sram_bv_done  <= 1'b0;
        end else begin
            state_q <= state_d;

            // 1-cycle pulse
            sram_rd <= 1'b0;

            case (state_q)
                S_IDLE: begin
                    bv_index     <= 5'd0;
                    sram_w_index <= 3'd0; // BV Address: w0-w4
                    sram_bv_done <= 1'b0;
                end

                S_RTU_LOAD: begin
                    sram_bv_done <= 1'b0;
                    if (bv_count != 5'd0) begin
                        sram_addr    <= 9'd17; // 1st BV Address start at 17
                        sram_w_index <= 3'd0; // BV Address reset to w0
                        sram_rd      <= 1'b1; // Override global sram_rd <= 1'b0 for 1-cycle
                        bv_index     <= 5'd0;
                    end
                end

                S_SRAM_READ: begin
                    // Iterative SRAM Read
                    if (sram_valid) begin
                        if (sram_w_index != 3'd4) begin
                            sram_w_index <= sram_w_index + 3'd1; // BV Address iterate through w0-w4
                            sram_rd      <= 1'b1; // Override global sram_rd <= 1'b0 for 1-cycle
                            sram_addr    <= sram_addr + 9'd16; // BV Address = 17 + 5 * i + word (16 bit)
                        end else begin
                            if (bv_index == (bv_count - 5'd1)) begin
                                sram_bv_done <= 1'b1;
                            end else begin
                                bv_index     <= bv_index + 5'd1;
                                sram_w_index <= 3'd0; // BV Address reset to w0
                                sram_rd      <= 1'b1; // Override global sram_rd <= 1'b0 for 1-cycle
                                sram_addr    <= sram_addr + 9'd16; // BV Address = 17 + 5 * i + word (16 bit)
                            end
                        end
                    end
                end

                S_DECODE: begin
                    sram_bv_done <= 1'b0; // Clear tag after state transistion
                end

                S_CAL: begin
                end

                default: ;
            endcase
        end
    end

endmodule