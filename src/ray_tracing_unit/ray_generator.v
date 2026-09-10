`default_nettype none
`include "tinytracer_defs.vh"

module ray_generator (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                mode,            // mode = 0 for primary ray generation, 1 otherwise  

    // Primary Ray Signals
    input  wire [3*`WLEN-1:0]  camera_viewport, // TBD, ask elvis

    // Secondary Ray Signals
    input  wire [3*`WLEN-1:0]  collision_point, // Point of ray-object intersection
    input  wire [3*`WLEN-1:0]  surface_norm,    // Surface normal vector of ray-object intersection
    input  wire [3*`WLEN-1:0]  ray_dir,         // Incident ray direction 
    input  wire [1:0]          mat_type,        // Type of material that was hit by ray  

    // Generated Ray Signals
    output reg  [3*`WLEN-1:0]  gen_ray_origin,  // Origin of generated ray
    output reg  [3*`WLEN-1:0]  gen_ray_dir,     // Direction of generated ray
    output reg                 gen_ray_valid,   // Generated rays are valid unless they are from emissive material

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
