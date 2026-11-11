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

  // Request selection (see truth table in the docs)
  logic sel;        // 0 = I/O Unit, 1 = RTU
  logic req_valid;  // 1 = exactly one valid request is present

  // Selected request
  logic [tinytracer_pkg::ADDR_WIDTH-1:0] req_addr;
  logic [tinytracer_pkg::DATA_WIDTH-1:0] req_data;
  logic                                  req_wen;

  // Registered SRAM request
  logic [tinytracer_pkg::ADDR_WIDTH-1:0] addr_q;
  logic [tinytracer_pkg::DATA_WIDTH-1:0] data_q;
  logic                                  wen_q;
  logic                                  is_read_q;
  logic                                  valid_q;

  // Response and handshake
  logic resp_valid_q;
  logic req_accepted;
  logic can_accept;

  // Accept a new request when the previous operation has completed
  // and any pending response can be consumed.
  assign can_accept = !valid_q && (!resp_valid_q || rtu_rd.resp_ready);

  // Truth table
  assign req_valid = io_wr.req_valid ^ rtu_rd.req_valid;
  assign sel       = !io_wr.req_valid && rtu_rd.req_valid;

  // Ready signals: only when a single valid request is present
  assign io_wr.req_ready  = rst_n && can_accept && req_valid && !sel;
  assign rtu_rd.req_ready = rst_n && can_accept && req_valid &&  sel;

  // Request handshake
  assign req_accepted =
    (io_wr.req_valid  && io_wr.req_ready) ||
    (rtu_rd.req_valid && rtu_rd.req_ready);

  // Request mux: sel chooses the source once req_valid is 1
  always_comb begin
    req_addr = '0;
    req_data = '0;
    req_wen  = 1'b0;

    if (req_valid) begin
      if (!sel) begin
        // I/O write
        req_addr = io_wr.req_waddr;
        req_data = io_wr.req_wdata;
        req_wen  = io_wr.req_wen;
      end
      else begin
        // RTU read
        req_addr = rtu_rd.req_raddr;
      end
    end
  end

  // Register accepted request
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      addr_q    <= '0;
      data_q    <= '0;
      wen_q     <= 1'b0;
      is_read_q <= 1'b0;
      valid_q   <= 1'b0;
    end
    else begin
      valid_q <= req_accepted;

      if (req_accepted) begin
        addr_q    <= req_addr;
        data_q    <= req_data;
        wen_q     <= req_wen;
        is_read_q <= sel;
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
      if (valid_q && is_read_q)
        resp_valid_q <= 1'b1;
      else if (resp_valid_q && rtu_rd.resp_ready)
        resp_valid_q <= 1'b0;
    end
  end

  assign rtu_rd.resp_valid = resp_valid_q;
  assign rtu_rd.resp_rdata = dout;

endmodule

