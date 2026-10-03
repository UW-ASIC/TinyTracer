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

logic [(tinytracer_pkg::WLEN-1) : 0] regs [7 : 0]; 

always_ff @(posedge clk) begin 
    if (!rst_n) begin 
        // Reset all registers to 0
        for (integer i = 0; i < 8; i++) begin
            regs[i] <= '0; 
        end
    end else begin 
        if (load) begin 
            // R0-R2 <- load_u.{x,y,z}
            regs[0] <= load_u.x; 
            regs[1] <= load_u.y;
            regs[2] <= load_u.z; 

            // R3-R5 <- load_v.{x,y,z}
            regs[3] <= load_v.x; 
            regs[4] <= load_v.y;
            regs[5] <= load_v.z; 
        end else if (wen) begin 
            regs[waddr] <= wdata; 
        end 
    end 
end 

always_comb begin 
    // Outputs 
    rdata1 = regs[raddr1]; 
    rdata2 = regs[raddr2]; 
    result.x = regs[0]; 
    result.y = regs[1]; 
    result.z = regs[2]; 
end 

endmodule
