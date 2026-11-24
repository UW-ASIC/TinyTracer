`default_nettype wire

// Flat-port wrapper around pixel_tx: cocotb can't drive interface ports.
module pixel_tx_tb (
    input  logic        clk,
    input  logic        rst_n,

    input  logic        pixel_valid,
    input  logic [23:0] pixel_colour,   // {r, g, b}
    output logic        pixel_ready,

    output logic        tx_valid,
    output logic [7:0]  tx_data,
    input  logic        tx_ready
);

    colour_if #(.W(tinytracer_pkg::COLOUR_DEPTH)) pixel ();
    stream_if #(.W(8)) tx ();

    assign pixel.valid  = pixel_valid;
    assign pixel.colour = pixel_colour;
    assign pixel_ready  = pixel.ready;

    assign tx_valid = tx.valid;
    assign tx_data  = tx.data;
    assign tx.ready = tx_ready;

    pixel_tx dut (.clk(clk), .rst_n(rst_n), .pixel(pixel), .tx(tx));

endmodule
