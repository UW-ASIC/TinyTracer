`default_nettype none
`include "tinytracer_defs.vh"

module intersection_unit (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                prim_type,       // Primitive type
    input  wire [3*`WLEN-1:0]  ray_origin,      // Incident ray origin
    input  wire [3*`WLEN-1:0]  ray_dir,         // Incident ray direction 
    input  wire [3*`WLEN-1:0]  origin,          // Sphere/triangle origin
    input  wire [3*`WLEN-1:0]  u,               // Triangle u vector
    input  wire [3*`WLEN-1:0]  v,               // Triangle v vector
    input  wire [`WLEN-1:0]    radius,          // Sphere radius 
    output reg  [3*`WLEN-1:0]  collision_point, // Point of ray-object intersection
    output reg                 hit,             // Object hit flag  

    ////////////////////////////////
    //  RTU <-> Decode Interface  //
    ////////////////////////////////

    // Macro-op Request Channel
    output wire                macro_req_valid,
    output wire [`MACRO_W-1:0] macro_req_op,
    input  wire                macro_req_ready,
    
    // Macro-op Response Channel
    output wire                macro_resp_ready,
    input  wire                macro_resp_valid,
    input  wire [3*`WLEN-1:0]  macro_resp_result
);

endmodule
