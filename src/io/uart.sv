`default_nettype wire

module uart (
    input  logic       clk,
    input  logic       rst_n,

    input  logic       clkq,

    // UART <-> I/O Interface
    stream_if.src      rx,      // receive byte stream, to I/O
    stream_if.sink     tx,      // transmit byte stream, from I/O

    // UART <-> Host Device Interface
    input  logic       TT_RX,
    output logic       TT_TX
);

// ------------------------
// Internal Signals

    // CDC
    reg rx_meta;
    reg rx_sync;

    // RX oversampling
    reg [3:0] rx_ctr; // sample 0-15
    reg [2:0] rx_bit_ctr; // data bit 0-7

    reg rx_sample_6;
    reg rx_sample_8;
    reg rx_sample_10;

    // majority vote between the 3 samples to produce the final value
    wire rx_majority;
    assign rx_majority =
        (rx_sample_6 & rx_sample_8) |
        (rx_sample_6 & rx_sample_10) |
        (rx_sample_8 & rx_sample_10);

  
   
    reg [7:0] rx_shift_reg;

    // TX timing
    reg [3:0] tx_ctr; // must hold bit for 16 cycles of clkq
    reg [3:0] tx_bit_ctr; // start bit, d0-7, stop bit

    reg [9:0] tx_shift_reg;

    assign TT_TX = (tx_state == TX_IDLE) ? 1'b1 : tx_shift_reg[0]; 
    assign tx.ready = (tx_state == TX_IDLE);

  
    localparam RX_IDLE  = 2'd0;  //  waiting for the RX line to go low
    localparam RX_START = 2'd1;  //  sampling the possible start bit at 6, 8, and 10
    localparam RX_DATA  = 2'd2;  //  receiving d0 through d7
    localparam RX_STOP  = 2'd3;  //  sampling and validating the stop bit

    reg [1:0] rx_state;

    localparam TX_IDLE = 1'd0;  //  no byte is currently being transmitted
    localparam TX_SEND = 1'd1;  //  a framed byte is being serialized

    reg tx_state;

    reg clkq_meta;
    reg clkq_sync;
    reg clkq_prev;

    wire clkq_tick = clkq_sync && !clkq_prev;


// ------------------------

    // we are assuming clk >>> clkq, we want to have sync logic for clkq since the rest of the uart module relies on clk


    always @(posedge clk) begin
        if (!rst_n) begin
            clkq_meta <= 1'b0;
            clkq_sync <= 1'b0;
            clkq_prev <= 1'b0;
        end
        else begin
            clkq_meta <= clkq;
            clkq_sync <= clkq_meta;
            clkq_prev <= clkq_sync;
        end
    end


    // CDC

    // synchronize incoming signal to clkq before using
 
    always @(posedge clk) begin
        if (!rst_n) begin
            rx_meta <= 1'b1;
            rx_sync <= 1'b1;  // UART is idle high, so both registers must be reset to 1
        end
        else begin
            rx_meta <= TT_RX;
            rx_sync <= rx_meta;
        end
    end


    // RX OVERSAMPLING / RX CONTROLLER

    // we are using clkq to sample each incoming bit 16 times
    // near the centre of each bit (6,8,10) out of 16 samples, we do a majority vote to reduce sensitivity to edge timing


    always @(posedge clk) begin
        if (!rst_n) begin
            rx_state     <= RX_IDLE;
            rx_ctr       <= 4'd0;
            rx_bit_ctr   <= 3'd0;
            rx_shift_reg <= 8'd0;

            rx_sample_6  <= 1'b1;
            rx_sample_8  <= 1'b1;
            rx_sample_10 <= 1'b1;

            rx.valid     <= 1'b0;
            rx.data      <= 8'd0;
        end
        else begin

            // when both rx.valid and rx.ready, the data is recieved and we can clear the valid bit to begin the next cycle
            // we currently assume we cannot backpressure RX (data is recieved faster than other downstream elements can consume it)
            // so we do not need logic for 

            if (rx.valid && rx.ready) begin
                rx.valid <= 1'b0;
            end
            

             case (rx_state)
                RX_IDLE: begin
                    rx_ctr <= 4'd0;

                    if (rx_sync == 1'b0) begin
                        rx_state <= RX_START;
                    end
                end

                

                RX_START: begin
                    if (clkq_tick) begin
        
                    if (rx_ctr == 4'd6)
                        rx_sample_6 <= rx_sync;

                    if (rx_ctr == 4'd8)
                        rx_sample_8 <= rx_sync;

                    if (rx_ctr == 4'd10)
                        rx_sample_10 <= rx_sync;

                    if (rx_ctr == 4'd15) begin
                        rx_ctr <= 4'd0;

                        if (!rx_majority) begin
                            rx_state <= RX_DATA; // majority 0 is a valid start
                            rx_bit_ctr <= 3'd0;
                        end 
                        else begin
                            rx_state <= RX_IDLE; // majority 1 is an invalid start
                        end

                    end
                    else begin
                        rx_ctr <= rx_ctr + 1'b1;
                    end
                    end

                end

                RX_DATA: begin
                    if (clkq_tick) begin
                    if (rx_ctr == 4'd6)
                        rx_sample_6 <= rx_sync;

                    if (rx_ctr == 4'd8)
                        rx_sample_8 <= rx_sync;

                    if (rx_ctr == 4'd10)
                        rx_sample_10 <= rx_sync;

                    if (rx_ctr == 4'd15) begin
                        rx_ctr <= 4'd0;
                    // shift majority voted data bit into shift reg
                        rx_shift_reg <= {rx_majority, rx_shift_reg[7:1]}; // we shift in our new bit to the shift register
                        if (rx_bit_ctr == 3'd7) begin
                            rx_state <= RX_STOP;
                        end
                        else begin
                            rx_bit_ctr <= rx_bit_ctr + 1'b1;
                        end

                    end
                    else begin
                        rx_ctr <= rx_ctr + 1'b1;
                    end  
                    end              
                end

                RX_STOP: begin
                    if (clkq_tick) begin

                    if (rx_ctr == 4'd6)
                        rx_sample_6 <= rx_sync;

                    if (rx_ctr == 4'd8)
                        rx_sample_8 <= rx_sync;

                    if (rx_ctr == 4'd10)
                        rx_sample_10 <= rx_sync;

                    if (rx_ctr == 4'd15) begin
                        rx_ctr <= 4'd0;

                        // stop bit must be high, otherwise we discard the frame if it has invalid stop
                        if (rx_majority) begin
                            rx.data  <= rx_shift_reg;
                            rx.valid <= 1'b1; // we hold this as valid until downstream interface acknowledges with rx.ready that the byte is recieved
                        end

                        rx_state <= RX_IDLE;

                    end
                    else begin
                        rx_ctr <= rx_ctr + 1'b1;
                    end
                    
                end
                end
                // not required in final rtl, but recovers safely if state ever becomes invalid - same goes for the default case on TX, if we do need to reduce cell ct we can here
                default: begin
                    rx_state <= RX_IDLE;
                    rx_ctr     <= 4'd0;
                    rx_bit_ctr <= 3'd0;
                end

            endcase
        end
    end


   

    always @(posedge clk) begin
        if (!rst_n) begin
            tx_state     <= TX_IDLE;
            tx_ctr       <= 4'd0;
            tx_bit_ctr   <= 4'd0;
            tx_shift_reg <= 10'h3FF; // keeps UART TX reg at idle high when reset
        end
        else begin  
            case (tx_state)
                TX_IDLE: begin
                    tx_ctr     <= 4'd0;
                    tx_bit_ctr <= 4'd0;
                    
                    

                    if (tx.valid && tx.ready) begin

                        // loading in the shift register as STOP, D7-D0, START) so that bit 0 is always the one we transmit as we shift the register
                        tx_shift_reg <= {1'b1, tx.data, 1'b0};
                        tx_state <= TX_SEND;
                    end
                end

                TX_SEND: begin
                    if (clkq_tick) begin

                    // holding each bit for 16 cycles before shifting in the next bit since clkq is baud*16
                    if (tx_ctr == 4'd15) begin
                        tx_ctr <= 4'd0;

                        tx_shift_reg <= {1'b1, tx_shift_reg[9:1]};

                        if (tx_bit_ctr == 4'd9) begin
                            tx_state   <= TX_IDLE;
                            tx_bit_ctr <= 4'd0;
                        end
                        else begin 
                            tx_bit_ctr <= tx_bit_ctr + 1'b1;
                        end
                    end
                    else begin
                        tx_ctr <= tx_ctr + 1'b1;
                    end
                    end
                end
                default: begin
                    tx_state <= TX_IDLE;
                    tx_ctr <= 4'd0;
                    tx_bit_ctr <= 4'd0;
                end

            endcase
        end
    end
endmodule
