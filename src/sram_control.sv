`default_nettype wire

module sram_control (
    input  logic                                  clk,
    input  logic                                  rst_n,

    // I/O <-> SRAM Interface
    sram_wr_if.server                             io_wr,

    // RTU <-> SRAM Interface
    sram_rd_if.server                             rtu_rd,

    // SRAM Control Signals
    output logic                                  wen,
    output logic [tinytracer_pkg::ADDR_WIDTH-1:0] addr,
    output logic [tinytracer_pkg::DATA_WIDTH-1:0] din,
    input  logic [tinytracer_pkg::DATA_WIDTH-1:0] dout
);

    // Request selection
    logic sel;

    // Selected request
    logic [tinytracer_pkg::ADDR_WIDTH-1:0] req_addr;
    logic [tinytracer_pkg::DATA_WIDTH-1:0] req_data;
    logic                                  req_wen;

    // Registered SRAM request
    logic [tinytracer_pkg::ADDR_WIDTH-1:0] addr_q;
    logic [tinytracer_pkg::DATA_WIDTH-1:0] data_q;
    logic                                  wen_q;
    logic                                  valid_q;

    // Response and handshake
    logic resp_valid_q;
    logic req_accepted;
    logic can_accept;

    // Accept a new request when the previous operation
    // has completed and any response can be consumed.
    assign can_accept =
        !valid_q &&
        (!resp_valid_q || rtu_rd.resp_ready);

    // Request arbitration
    always_comb begin
        sel = 1'b0;

        if (!io_wr.req_valid && rtu_rd.req_valid)
            sel = 1'b1;
    end

    // Ready signals
    always_comb begin
        io_wr.req_ready  = 1'b0;
        rtu_rd.req_ready = 1'b0;

        if (rst_n && can_accept) begin
            if (io_wr.req_valid && !rtu_rd.req_valid)
                io_wr.req_ready = 1'b1;

            else if (!io_wr.req_valid && rtu_rd.req_valid)
                rtu_rd.req_ready = 1'b1;
        end
    end

    // Request handshake
    assign req_accepted =
        (io_wr.req_valid  && io_wr.req_ready) ||
        (rtu_rd.req_valid && rtu_rd.req_ready);

    // Request mux
    always_comb begin
        req_addr = '0;
        req_data = '0;
        req_wen  = 1'b0;

        if (!sel) begin
            // I/O write
            req_addr = io_wr.req_waddr;
            req_data = io_wr.req_wdata;
            req_wen  = io_wr.req_wen;
        end
        else begin
            // RTU read
            req_addr = rtu_rd.req_raddr;
            req_data = '0;
            req_wen  = 1'b0;
        end
    end

    // Register accepted request
    always_ff @(posedge clk) begin
        if (!rst_n) begin
            addr_q  <= '0;
            data_q  <= '0;
            wen_q   <= 1'b0;
            valid_q <= 1'b0;
        end
        else begin
            valid_q <= req_accepted;

            if (req_accepted) begin
                addr_q <= req_addr;
                data_q <= req_data;
                wen_q  <= req_wen;
            end
        end
    end

    // SRAM outputs
    assign addr = addr_q;
    assign din  = data_q;
    assign wen  = valid_q && wen_q;

    // Read response valid tracking
    always_ff @(posedge clk) begin
        if (!rst_n) begin
            resp_valid_q <= 1'b0;
        end
        else begin
            if (valid_q && !wen_q)
                resp_valid_q <= 1'b1;

            else if (resp_valid_q && rtu_rd.resp_ready)
                resp_valid_q <= 1'b0;
        end
    end

    assign rtu_rd.resp_valid = resp_valid_q;
    assign rtu_rd.resp_rdata = dout;

endmodule