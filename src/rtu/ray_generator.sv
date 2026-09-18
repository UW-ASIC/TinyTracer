`default_nettype wire
/* verilator lint_off IMPORTSTAR */
import tinytracer_pkg::*;
/* verilator lint_on IMPORTSTAR */

module ray_generator (
    input  logic                            clk,
    input  logic                            rst_n,
    input  logic                            mode,            // mode = 0 for primary ray generation, 1 otherwise

    // Secondary Ray Signals
    input  tinytracer_pkg::vec3_t           collision_point, // Point of ray-object intersection
    input  tinytracer_pkg::vec3_t           ray_dir,         // Incident ray direction
    input  tinytracer_pkg::mat_type_t       mat_type,        // Type of material that was hit by ray

    // Generated Ray Signals
    output tinytracer_pkg::vec3_t           gen_ray_origin,  // Origin of generated ray
    output tinytracer_pkg::vec3_t           gen_ray_dir,     // Direction of generated ray
    output logic                            gen_ray_valid,   // Generated rays are valid unless they are from emissive material

    // RTU <-> Decode Interface
    macro_if.client                         macro
);

endmodule
