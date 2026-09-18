`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module intersection_unit (
    input  logic                            clk,
    input  logic                            rst_n,
    input  tinytracer_pkg::prim_type_t      prim_type,       // Primitive type
    input  tinytracer_pkg::vec3_t           ray_origin,      // Incident ray origin
    input  tinytracer_pkg::vec3_t           ray_dir,         // Incident ray direction
    input  tinytracer_pkg::vec3_t           origin,          // Sphere/triangle origin
    input  tinytracer_pkg::vec3_t           u,               // Triangle u vector
    input  tinytracer_pkg::vec3_t           v,               // Triangle v vector
    input  logic [WLEN-1:0]                 radius,          // Sphere radius
    output tinytracer_pkg::vec3_t           collision_point, // Point of ray-object intersection
    output logic                            hit,             // Object hit flag
    
    // RTU <-> Decode Interface
    macro_if.client                         macro
);

endmodule
