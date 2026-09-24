/* verilator lint_off UNUSEDPARAM */
package tinytracer_pkg;

  //---------------------------- System-wide defaults --------------------------
  localparam int ADDR_WIDTH   = 8;           // SRAM address width
  localparam int DATA_WIDTH   = 16;          // SRAM word width
  localparam int DIM_WIDTH    = 12;          // image width/height (two RENDER bytes each)
  localparam int SPP          = 8;           // samples per pixel (power of two)
  localparam int COLOUR_DEPTH = 8;           // bits per colour channel
  localparam int MAX_BOUNCES  = 10;          // maximum ray bounces
  localparam int WLEN         = 16;          // word length

  //---------------------------- Fixed point -----------------------------------
  // Q8.8 signed two's complement: range [-128.0, +127.99609375], LSB = 2^-8.
  localparam int Q_INT  = 8;
  localparam int Q_FRAC = 8;

  //---------------------------- UART frame encoding ---------------------------
  // Plain constants rather than an enum: RENDER_START and PIXEL_START share a
  // value, which an enum does not allow.
  localparam logic [7:0] RENDER_START = 8'h00;
  localparam logic [7:0] OBJ_START    = 8'h01;
  localparam logic [7:0] PIXEL_START  = 8'h00;

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
  // {u3, u2, u1, v3, v2, v1, MACROOP} = 6*16 + 5 = 101 bits
  // See docs/encoding/instruction.md
  localparam int MACRO_W   = 101;
  localparam int MACROOP_W = 5;

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
    M_COS         = 5'b01001,  // cosine
    M_RECP        = 5'b01010,  // reciprocal
    M_MAG         = 5'b01011,  // 2D vector magnitude
    M_VADD        = 5'b01100,  // vector addition
    M_VSUB        = 5'b01101,  // vector subtraction
    M_SCAL_VEC    = 5'b01110,  // scalar-vector multiplication
    M_DOT         = 5'b01111,  // vector dot product
    M_CROSS       = 5'b10000,  // vector cross product
    M_NORM        = 5'b10001,  // vector normalization
    M_SPHERE_NORM = 5'b10010   // vector normalization using sphere radius
  } macro_op_t;

  // Macro-op word: | u3 | u2 | u1 | v3 | v2 | v1 | MACROOP |
  typedef struct packed {
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
    U_COS  = 4'b1001,  // cosine
    U_RECP = 4'b1010,  // reciprocal
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
  // DIV/SQRT/COS/RECP/MAG -> CORDIC
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

  typedef enum logic [2:0] {
    CORDIC_DIV  = 3'b000,
    CORDIC_SQRT = 3'b001,
    CORDIC_COS  = 3'b010,
    CORDIC_RECP = 3'b011,
    CORDIC_MAG  = 3'b100
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

  //---------------------------- Memory map ------------------------------------
  // Bounding volumes are 5 words each (see docs/encoding/scene.md), so the
  // primitives start NUM_BV * 5 words after BV_BASE. The CORDIC LUT lives in a
  // ROM local to the CORDIC unit, not in SRAM.
  localparam logic [ADDR_WIDTH-1:0] BV_BASE  = 8'h00;
  localparam int                    NUM_BV   = 4;
  localparam logic [ADDR_WIDTH-1:0] OBJ_BASE = 8'h14;

endpackage
/* verilator lint_on UNUSEDPARAM */
