`default_nettype wire

module reg_file (
    input  logic        clk,
    input  logic        rst_n,

    // Parallel Load (Decode): R0-R2 <- load_u.{x,y,z}, R3-R5 <- load_v.{x,y,z}
    input  logic                   load,
    input  tinytracer_pkg::vec3_t  load_u,
    input  tinytracer_pkg::vec3_t  load_v,

    // Macro-op Result (Decode): {R2, R1, R0}
    output tinytracer_pkg::vec3_t  result,

    // Write Port (FU Control)
    input  logic            wen,
    input  logic [2:0]      waddr,
    input  logic [tinytracer_pkg::WLEN-1:0] wdata,

    // Read Ports (FU Control)
    input  logic [2:0]      raddr1,
    output logic [tinytracer_pkg::WLEN-1:0] rdata1,
    input  logic [2:0]      raddr2,
    output logic [tinytracer_pkg::WLEN-1:0] rdata2
);

import tinytracer_pkg::*;

logic [WLEN-1:0] register [0:5]; // R0, R1, ... , R5

// WRITE PORT 

always @(posedge clk or negedge rst_n) begin 
    if (!rst_n) begin 
        for (int i = 0; i <= 5; i++) begin // reset all registers to 0 if !rst_n
            register [i] <= 1'b0;
        end
    end
    else begin
        if (load) begin
            register[0] <= load_u.x; // load in the register values
            register[1] <= load_u.y;
            register[2] <= load_u.z;

            register[3] <= load_v.x;
            register[4] <= load_v.y;
            register[5] <= load_v.z;
        end

        if (wen) begin // write enable
            register[waddr] <= wdata;
        end
    end
end


// READ PORT 

assign rdata1 = register[raddr1];
assign rdata2 = register[raddr2];

assign result.x = register[0]; // reg file R0-R2 sent to RTU as macro op result - is this correct mapping?
assign result.y = register[1];
assign result.z = register[2];


endmodule
