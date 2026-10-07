`default_nettype wire

module multiplier #(
    parameter WLEN = 16
)( // 16 bit array multiplier
    input  logic                clk,
    input  logic                rst_n,
    input  logic [WLEN-1:0]     multiplicand,
    input  logic [WLEN-1:0]     multiplier_in,
    output logic [WLEN*2-1:0]   product,
    // FU <-> Multiplier Interface
    fu_if.server                fu     
);

    // partial products ///////////////
    logic [WLEN-1:0] pp [WLEN];
    genvar i, j;
    generate
        for (i = 0; i < WLEN; i++) begin : g_ppg
            ppg u_ppg (
                .multiplicand_bit(multiplicand[i]),
                .multiplier(multiplier_in),
                .pp(pp[i])
            );
        end
    endgenerate

    // adder tree //////////////////

    logic [WLEN-1:0]    row_sum [WLEN]; // sum outputs of row i
    logic               row_cout[WLEN]; // carry outputs of row i
    logic [WLEN-1:0]    row_b   [WLEN]; // addend from prev row, shifted right by 1
    logic [WLEN*2-1:0]  product_comb;

    // row 0 special case
    assign row_sum      [0] = pp[0]; 
    assign row_cout     [0] = 1'b0;
    assign product_comb [0] = row_sum[0][0];

    generate
        for (i = 1; i < WLEN; i++) begin : g_row
            // prev row result shifted down 1 weight, cout becomes MSB
            assign row_b[i] = {row_cout[i-1], row_sum[i-1][WLEN-1:1]};
            logic [WLEN-1:0] carry; // cout of each bit in row

            //bit 0 has no cin
            half_adder u_ha (
                .a      (pp[i][0]),
                .b      (row_b[i][0]),
                .sum    (row_sum[i][0]),
                .cout   (carry[0])
            );

            for (j = 1; j < WLEN; j++) begin : g_col
                full_adder u_fa (
                    .a      (pp[i][j]),
                    .b      (row_b[i][j]),
                    .cin    (carry[j-1]),
                    .sum    (row_sum[i][j]),
                    .cout   (carry[j])
                );
            end
            assign row_cout[i]      = carry[WLEN-1];
            assign product_comb[i]  = row_sum[i][0]; // collect product
        end
    endgenerate

    // upper half from last row
    assign product_comb [WLEN*2-1:WLEN] = {row_cout[WLEN-1], row_sum[WLEN-1][WLEN-1:1]};

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) product <= '0;
        else        product <= product_comb;
    end

endmodule

/////////////////////

module ppg #(
    parameter WLEN = 16
)(
    input  logic            multiplicand_bit,
    input  logic [WLEN-1:0] multiplier,
    output logic [WLEN-1:0] pp // aligned
);

    assign pp = multiplier & {WLEN{multiplicand_bit}};


endmodule

////////////////////

module half_adder (
    input  logic        a,
    input  logic        b,
    output logic        sum,
    output logic        cout
);
    assign sum = a ^ b;
    assign cout = a & b;
endmodule

////////////////////

module full_adder (
    input  logic        a,
    input  logic        b,
    input  logic        cin,
    output logic        sum,
    output logic        cout
);
    logic s1, c1, c2;
    half_adder ha1(.a(a), .b(b), .sum(s1), .cout(c1));
    half_adder ha2(.a(s1), .b(cin), .sum(sum), .cout(c2));
    assign cout = c1 | c2;

endmodule