`default_nettype wire

// Sends each pixel from the Accumulator to the host as a PIXEL message:
// PIXEL_START, R, G, B, with DLE in front of any colour byte that is 0x00 or
// 0x03. See docs/encoding/uart_frame.md.
module pixel_tx (
    input  logic       clk,
    input  logic       rst_n,

    colour_if.sink     pixel,   // pixel colour {r, g, b}, from Accumulator
    stream_if.src      tx       // byte stream, to UART
);

    // The pixel is copied on accept so the Accumulator is free for the next
    // one while these bytes go out. The current colour byte is always the top
    // 8 bits; the register shifts left by 8 after each colour byte.
    logic [3*tinytracer_pkg::COLOUR_DEPTH-1:0] colour_reg;
    logic [1:0] byte_idx;   // 0 = PIXEL_START, 1 = R, 2 = G, 3 = B
    logic       esc_sent;   // DLE for the current colour byte already sent
    logic       busy;       // a pixel is held and being sent

    // Current byte: PIXEL_START first, then the top byte of colour_reg.
    logic [7:0] colour_byte;
    logic [7:0] cur_byte;
    logic       need_escape;

    assign colour_byte = colour_reg[3*tinytracer_pkg::COLOUR_DEPTH-1 -: 8];
    assign cur_byte    = (byte_idx == 2'd0) ? tinytracer_pkg::PIXEL_START : colour_byte;

    // A colour byte of 0x00 or 0x03 would look like a start byte or DLE to
    // the host, so DLE goes out first. 0x01 is not escaped in this direction.
    assign need_escape = (byte_idx != 2'd0) && !esc_sent &&
                         (colour_byte == tinytracer_pkg::PIXEL_START ||
                          colour_byte == tinytracer_pkg::DLE);

    assign tx.valid = busy;
    assign tx.data  = need_escape ? tinytracer_pkg::DLE : cur_byte;

    // Take a new pixel only when the last one is fully sent.
    assign pixel.ready = !busy;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            colour_reg <= '0;
            byte_idx   <= 2'd0;
            esc_sent   <= 1'b0;
            busy       <= 1'b0;
        end else if (pixel.valid && pixel.ready) begin
            colour_reg <= pixel.colour;
            byte_idx   <= 2'd0;
            esc_sent   <= 1'b0;
            busy       <= 1'b1;
        end else if (tx.valid && tx.ready) begin
            if (need_escape) begin
                // DLE went out; the colour byte itself goes next.
                esc_sent <= 1'b1;
            end else if (byte_idx == 2'd3) begin
                // B went out: pixel done, ready for the next one.
                busy     <= 1'b0;
                esc_sent <= 1'b0;
            end else begin
                // Start byte, R or G went out: move to the next byte.
                // After a colour byte, shift so the next one is on top.
                byte_idx <= byte_idx + 2'd1;
                esc_sent <= 1'b0;
                if (byte_idx != 2'd0)
                    colour_reg <= colour_reg << 8;
            end
        end
    end

endmodule
