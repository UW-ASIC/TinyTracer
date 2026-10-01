`default_nettype wire

// Reads and writes the RTU's shared header and ray state registers; the
// signals for that and for operand source selects are not defined yet (see
// docs/modules/rtu/rtu.md, Handshakes).
module intersection_unit (
    input  logic                            clk,
    input  logic                            rst_n,

    // Controller <-> Intersection Unit Signals (start, done: one-cycle pulses)
    input  logic                            start,           // Start signal from the Controller; mode valid with it
    input  logic [1:0]                      mode,            // 0: search, 1: read the closest object, 2: hit point and normal
    output logic                            done,            // Mode finished
    output tinytracer_pkg::hit_kind_t       hit_kind,        // Search result, valid with done in mode 0
    output tinytracer_pkg::mat_type_t       material,        // Closest object's material, valid with done in mode 1

    // Intersection Unit <-> RTU Request Path Interface
    rtu_req_if.client                       req,

    // Intersection Unit <-> SRAM Interface (connected by the RTU while active)
    sram_rd_if.client                       sram
);

endmodule
