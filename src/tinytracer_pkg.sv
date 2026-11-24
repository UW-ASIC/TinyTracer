// Shared constants and types. Other files refer to them by qualified name
// (tinytracer_pkg::WLEN) instead of `import tinytracer_pkg::*;`, because the
// Yosys that the Tiny Tapeout flow pins (yowasp-yosys 0.48) rejects imports.
/* verilator lint_off UNUSEDPARAM */
package tinytracer_pkg;

  //---------------------------- System-wide defaults --------------------------
  localparam int ADDR_WIDTH   = 9;           // SRAM address width (512 words)
  localparam int DATA_WIDTH   = 16;          // SRAM word width
  localparam int DIM_WIDTH    = 12;          // image width/height (two RENDER bytes each)
  localparam int PIX_W        = 9;           // pixel x and y counters (images up to 512 x 512)
  localparam int MAX_SPP      = 32;          // largest samples per pixel (the header sets each render's)
  localparam int SPP_LOG2_W   = 3;           // log2(samples per pixel), 0..5, from header word 15
  localparam int COLOUR_DEPTH = 8;           // bits per pixel colour channel
  localparam int SAMPLE_DEPTH = 12;          // bits per sample colour channel (glow can exceed 255)
  localparam int MAX_BOUNCES  = 8;           // maximum ray bounces
  localparam int WLEN         = 16;          // word length

  //---------------------------- Fixed point -----------------------------------
  // Two 16-bit signed two's complement formats (docs/encoding/number_format.md):
  //   POS = Q9.7:  positions and distances, range [-256.0, +255.9921875], LSB = 2^-7
  //   DIR = Q2.14: directions, range [-2.0, +1.99993896484375], LSB = 2^-14
  localparam int POS_FRAC = 7;
  localparam int DIR_FRAC = 14;

  //---------------------------- UART frame encoding ---------------------------
  // Plain constants rather than an enum: RENDER_START and PIXEL_START share a
  // value, which an enum does not allow.
  localparam logic [7:0] RENDER_START = 8'h00;
  localparam logic [7:0] OBJ_START    = 8'h01;
  localparam logic [7:0] PIXEL_START  = 8'h00;
  localparam logic [7:0] DLE          = 8'h03;  // data link escape: next byte is data

  //---------------------------- Vectors and colours ---------------------------
  // Packed structs: the first field is the most significant.
  // vec3_t maps the (u3, u2, u1) notation in docs/encoding/instruction.md to
  // z = u3, y = u2, x = u1, so x sits in the least significant word.
  typedef struct packed {
    logic [WLEN-1:0] z;
    logic [WLEN-1:0] y;
    logic [WLEN-1:0] x;
  } vec3_t;

  typedef struct packed {
    logic [COLOUR_DEPTH-1:0] r;
    logic [COLOUR_DEPTH-1:0] g;
    logic [COLOUR_DEPTH-1:0] b;
  } rgb_t;

  //---------------------------- Macro-op encoding -----------------------------
  // {FMT, u3, u2, u1, v3, v2, v1, MACROOP} = 1 + 6*16 + 5 = 102 bits
  // See docs/encoding/instruction.md
  localparam int MACRO_W   = 102;
  localparam int MACROOP_W = 5;

  // Number format select, carried with every macro-op and micro-op. MUL shifts
  // the 32-bit product right by 7 (FMT_POS) or 14 (FMT_DIR); SQRT works on POS
  // or DIR. Every other micro-op ignores it.
  typedef enum logic {
    FMT_POS = 1'b0,  // POS x POS -> POS; POS square root
    FMT_DIR = 1'b1   // product with a DIR operand; DIR square root
  } fmt_t;

  // Macro opcodes
  typedef enum logic [MACROOP_W-1:0] {
    M_ADD         = 5'b00000,  // scalar addition
    M_SUB         = 5'b00001,  // scalar subtraction
    M_EQ          = 5'b00010,  // == operator
    M_NE          = 5'b00011,  // != operator
    M_LT          = 5'b00100,  // < operator
    M_GE          = 5'b00101,  // >= operator
    M_MUL         = 5'b00110,  // scalar multiplication
    M_DIV         = 5'b00111,  // scalar division
    M_SQRT        = 5'b01000,  // scalar square root
    M_COS         = 5'b01001,  // scaled cosine, u1 * cos(v1)
                               // 5'b01010 unused
    M_MAG         = 5'b01011,  // 2D vector magnitude
    M_VADD        = 5'b01100,  // vector addition
    M_VSUB        = 5'b01101,  // vector subtraction
    M_SCAL_VEC    = 5'b01110,  // scalar-vector multiplication
    M_DOT         = 5'b01111,  // vector dot product
    M_CROSS       = 5'b10000,  // vector cross product
    M_NORM        = 5'b10001,  // vector normalization
    M_SPHERE_NORM = 5'b10010,  // vector normalization using sphere radius
    M_VMUL        = 5'b10011   // vector element-wise multiplication
  } macro_op_t;
  // M_ADD..M_MAG are scalar (one micro-op, opcode MACROOP[3:0], no ROM rows);
  // M_VADD..M_VMUL are vector (micro-ops from the Decode ROM).

  // Macro-op word: | FMT | u3 | u2 | u1 | v3 | v2 | v1 | MACROOP |
  typedef struct packed {
    fmt_t      fmt;
    vec3_t     u;
    vec3_t     v;
    macro_op_t op;
  } macro_word_t;

  //---------------------------- Micro-op encoding -----------------------------
  // {RD, RS1, RS2, MICROOP} = 3 + 3 + 3 + 4 = 13 bits
  localparam int MICRO_W   = 13;
  localparam int MICROOP_W = 4;

  // Micro opcodes
  typedef enum logic [MICROOP_W-1:0] {
    U_ADD  = 4'b0000,  // scalar addition
    U_SUB  = 4'b0001,  // scalar subtraction
    U_EQ   = 4'b0010,  // == operator
    U_NE   = 4'b0011,  // != operator
    U_LT   = 4'b0100,  // < operator
    U_GE   = 4'b0101,  // >= operator
    U_MUL  = 4'b0110,  // scalar multiplication
    U_DIV  = 4'b0111,  // scalar division
    U_SQRT = 4'b1000,  // scalar square root
    U_COS  = 4'b1001,  // scaled cosine, RS1 * cos(RS2)
                       // 4'b1010 unused
    U_MAG  = 4'b1011   // vector magnitude
  } micro_op_t;

  // Micro-op word: | RD | RS1 | RS2 | MICROOP |
  typedef struct packed {
    logic [2:0] rd;
    logic [2:0] rs1;
    logic [2:0] rs2;
    micro_op_t  op;
  } micro_word_t;

  // Functional unit select
  // ADD/SUB/EQ/NE/LT/GE -> ALU, MUL -> multiplier,
  // DIV/SQRT/COS/MAG -> CORDIC
  typedef enum logic [1:0] {
    FU_ALU    = 2'b00,
    FU_MUL    = 2'b01,
    FU_CORDIC = 2'b10
  } fu_sel_t;

  // Functional opcodes (the multiplier takes no opcode). fu_if carries the
  // opcode as a plain 3-bit field; each unit compares it against its own enum.
  typedef enum logic [2:0] {
    ALU_ADD = 3'b000,
    ALU_SUB = 3'b001,
    ALU_EQ  = 3'b010,
    ALU_NE  = 3'b011,
    ALU_LT  = 3'b100,
    ALU_GE  = 3'b101
  } alu_op_t;

  typedef enum logic [1:0] {
    CORDIC_DIV  = 2'b00,  // A / B
    CORDIC_SQRT = 2'b01,  // sqrt(A)
    CORDIC_COS  = 2'b10,  // A * cos(B)
    CORDIC_MAG  = 2'b11   // sqrt(A^2 + B^2)
  } cordic_op_t;

  //---------------------------- Scene encoding --------------------------------
  typedef enum logic [1:0] {
    MAT_DIFFUSE  = 2'b00,
    MAT_REFLECT  = 2'b01,
    MAT_DIELEC   = 2'b10,
    MAT_EMISSIVE = 2'b11
  } mat_type_t;

  typedef enum logic {
    PRIM_TRI = 1'b0,
    PRIM_SPH = 1'b1
  } prim_type_t;

  //---------------------------- RTU ---------------------------------------------
  // See docs/modules/rtu/rtu.md. Result of the Intersection Unit's search,
  // output with done in mode 0 and kept in the ray state registers.
  typedef enum logic [1:0] {
    HIT_SKY    = 2'b00,  // nothing hit, ray points up, or ground too far away
    HIT_GROUND = 2'b01,
    HIT_OBJECT = 2'b10
  } hit_kind_t;

  // Block that owns the request path and the SRAM read port (the Controller's
  // active register).
  typedef enum logic [1:0] {
    BLK_CTRL    = 2'b00,  // Controller, while it reads the header
    BLK_RAY_GEN = 2'b01,
    BLK_ISECT   = 2'b10,
    BLK_SHADER  = 2'b11
  } rtu_blk_t;

  // Scratch registers, shared by the Intersection Unit (test values) and the
  // Ray Generator (bounce values). Word i is scratch[i].
  localparam int SCRATCH_WORDS = 7;
  typedef logic [SCRATCH_WORDS-1:0][WLEN-1:0] scratch_t;

  //---------------------------- Memory map ------------------------------------
  // See docs/encoding/scene.md. The header is at address 0 and bounding volume
  // i at BV_BASE + BV_WORDS * i. The primitives follow the last bounding volume;
  // each one's address comes from its bounding volume's BV_START field. The
  // CORDIC LUT lives in a ROM local to the CORDIC unit, not in SRAM.
  localparam int HDR_WORDS = 17;         // header words, read once per render
  localparam int MAX_BV    = 16;         // largest bounding volume count
  localparam int BV_BASE   = HDR_WORDS;  // address of bounding volume 0
  localparam int BV_WORDS  = 5;          // words per bounding volume
  localparam int SPH_WORDS = 7;          // words per sphere
  localparam int TRI_WORDS = 12;         // words per triangle

endpackage
/* verilator lint_on UNUSEDPARAM */
