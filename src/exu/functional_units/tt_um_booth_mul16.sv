`default_nettype none

module tt_um_booth_mul16 (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);
  wire [1:0]  sel = uio_in[1:0];
  wire        wr  = uio_in[2];
  wire [31:0] p;
  reg  [15:0] a_q, b_q;
  reg  [31:0] p_q;

  always @(posedge clk) begin
    if (!rst_n) begin
      a_q <= 16'd0;
      b_q <= 16'd0;
      p_q <= 32'd0;
    end else begin
      if (wr) begin
        case (sel)
          2'd0: a_q[7:0]  <= ui_in;
          2'd1: a_q[15:8] <= ui_in;
          2'd2: b_q[7:0]  <= ui_in;
          2'd3: b_q[15:8] <= ui_in;
        endcase
      end
      p_q <= p;
    end
  end

  booth_mul16 u_mul (.a(a_q), .b(b_q), .p(p));

  assign uo_out  = p_q[8*sel +: 8];
  assign uio_out = 8'h00;
  assign uio_oe  = 8'h00;

  // List all unused inputs to prevent warnings
  wire _unused = &{ena, uio_in[7:3], 1'b0};

endmodule
