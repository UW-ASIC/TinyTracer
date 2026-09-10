`ifndef TINYTRACER_DEFS_VH
`define TINYTRACER_DEFS_VH

//---------------------------- System-wide defaults --------------------------
`define ADDR_WIDTH   9           // SRAM address width
`define DATA_WIDTH   16          // SRAM word width
`define BANK_WIDTH   4           // top address bits latched as SRAM bank
`define FCLK         50_000_000  // system clock frequency
`define BAUD         115_200     // UART baud rate
`define IMG_W        64          // Output image width
`define IMG_H        64          // Output image height
`define SPP          8           // samples per pixel (power of two)
`define COLOR_DEPTH  8           // bits per color channel 
`define MAX_BOUNCES  10          // maximum ray bounces
`define WLEN         16          // word length

//---------------------------- Fixed point -----------------------------------
// Q8.8 signed two's complement: range [-128.0, +127.99609375], LSB = 2^-8.
`define Q_INT        8
`define Q_FRAC       8
`define Q_ONE        16'h0100

//---------------------------- UART frame encoding ---------------------------
`define RENDER_START 8'h00   // RENDER_START 
`define OBJ_START    8'h01   // OBJ_START
`define PIXEL_START  8'h00   // PIXEL_START

//---------------------------- Macro-op encoding -----------------------------
// {u3, u2, u1, v3, v2, v1, MACROOP} = 6*16 + 5 = 101 bits
// See spec/instruction-encoding.md
`define MACRO_W       101
`define MACROOP_W     5

// Macro opcodes
`define M_ADD         5'b00000  // scalar addition
`define M_SUB         5'b00001  // scalar subtraction
`define M_EQ          5'b00010  // == operator
`define M_NE          5'b00011  // != operator
`define M_LT          5'b00100  // < operator
`define M_GE          5'b00101  // >= operator
`define M_MUL         5'b00110  // scalar multiplication
`define M_DIV         5'b00111  // scalar division
`define M_SQRT        5'b01000  // scalar square root
`define M_COS         5'b01001  // cosine
`define M_RECP        5'b01010  // reciprocal
`define M_RNG         5'b01011  // random number generator
`define M_VADD        5'b01100  // vector addition
`define M_VSUB        5'b01101  // vector subtraction
`define M_SCAL_VEC    5'b01110  // scalar-vector multiplication
`define M_DOT         5'b01111  // vector dot product
`define M_CROSS       5'b10000  // vector cross product
`define M_NORM        5'b10001  // vector normalization
`define M_SPHERE_NORM 5'b10010  // vector normalization using sphere radius

//---------------------------- Micro-op encoding -----------------------------
// {RD, RS1, RS2, MICROOP} = 3 + 3 + 3 + 4 = 13 bits
`define MICRO_W       13
`define MICROOP_W     4

// Micro opcodes
`define U_ADD         4'b0000   // scalar addition
`define U_SUB         4'b0001   // scalar subtraction
`define U_EQ          4'b0010   // == operator
`define U_NE          4'b0011   // != operator
`define U_LT          4'b0100   // < operator
`define U_GE          4'b0101   // >= operator
`define U_MUL         4'b0110   // scalar multiplication
`define U_DIV         4'b0111   // scalar division
`define U_SQRT        4'b1000   // scalar square root
`define U_COS         4'b1001   // cosine
`define U_RECP        4'b1010   // reciprocal
`define U_RNG         4'b1011   // random number generator

// Functional unit select
// ADD/SUB/EQ/NE/LT/GE -> ALU, MUL -> multiplier,
// DIV/SQRT/COS/RECP -> CORDIC, RNG -> RNG
`define FU_ALU        2'b00
`define FU_MUL        2'b01
`define FU_CORDIC     2'b10
`define FU_RNG        2'b11

// Functional opcodes (multiplier and RNG take no opcode)
`define ALU_ADD       3'b000
`define ALU_SUB       3'b001
`define ALU_EQ        3'b010
`define ALU_NE        3'b011
`define ALU_LT        3'b100
`define ALU_GE        3'b101

`define CORDIC_DIV    3'b000
`define CORDIC_SQRT   3'b001
`define CORDIC_COS    3'b010
`define CORDIC_RECP   3'b011

//---------------------------- Scene encoding --------------------------------
`define MAT_DIFFUSE  2'b00
`define MAT_REFLECT  2'b01
`define MAT_DIELEC   2'b10
`define MAT_EMISSIVE 2'b11
`define PRIM_TRI     1'b0
`define PRIM_SPH     1'b1

//---------------------------- Memory map ------------------------------------
`define LUT_BASE     9'h000
`define BV_BASE      9'h020
`define NUM_BV       4 
`define OBJ_BASE     9'h034

`endif // TINYTRACER_DEFS_VH
