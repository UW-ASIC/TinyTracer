`default_nettype none

// testbench wrapper for io module

// it instantiates io w the interface instances, then breaks out render / SRAM interface signals as top-level wires so cocotb can read them
// the parser input (rx_bytes) lives inside io, so cocotb reaches it hierarchically (dut.dut_io.rx_bytes.*) to inject byets directly.
// uart and clkdiv left idle, cuz this bench verifies the msg parser, not uart


module tb_io ();

  initial begin                                     // dump signals for waveform inspection
    $dumpfile("tb_io.vcd");
    $dumpvars(0, tb_io);
  end


  logic        clk;                                 // plain top level signals for cocotb to drive / observe
  logic        rst_n;
  logic [1:0]  clkdiv_ctl;
  logic [7:0]  clkdiv_data;
  logic        uart_rx;
  logic        uart_tx;


  render_if   render_bus ();                        // interface instances connected to io interface ports
  sram_wr_if  sram_bus ();

  // colour_if for pixel -- io uses colour_if.sink. Declared with the right type.
  colour_if #(.W(tinytracer_pkg::COLOUR_DEPTH)) colour_bus ();


  io dut_io (                                       // instantiate io w the interface instances and connecting everything
    .clk         (clk),
    .rst_n       (rst_n),
    .clkdiv_ctl  (clkdiv_ctl),
    .clkdiv_data (clkdiv_data),
    .render      (render_bus),
    .uart_rx     (uart_rx),
    .uart_tx     (uart_tx),
    .pixel       (colour_bus),
    .sram        (sram_bus)
  );

  // break out RENDER signals for observation
  wire render_strobe = render_bus.render;
  wire [tinytracer_pkg::DIM_WIDTH-1:0] render_img_w = render_bus.img_w;
  wire [tinytracer_pkg::DIM_WIDTH-1:0] render_img_h = render_bus.img_h;

  // break out SRAM write interface for observation
  wire sram_req_valid = sram_bus.req_valid;
  wire sram_req_wen = sram_bus.req_wen;
  wire [tinytracer_pkg::ADDR_WIDTH-1:0] sram_req_waddr = sram_bus.req_waddr;
  wire [tinytracer_pkg::DATA_WIDTH-1:0] sram_req_wdata = sram_bus.req_wdata;

  // sram ready is drivable from the test. 
  // backpressure test drives it low to hold a write, then high to release
  logic sram_req_ready_drv = 1'b1;
  assign sram_bus.req_ready = sram_req_ready_drv;

endmodule
