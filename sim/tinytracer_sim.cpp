// tinytracer_sim.cpp - model of the TinyTracer chip rendering flow. C++17, no libraries.
//
// Build:  g++ -O2 -std=c++17 tinytracer_sim.cpp -o tinytracer_sim
//         MSVC: cl /O2 /std:c++17 /EHsc tinytracer_sim.cpp
// Run:    tinytracer_sim scene_demo.txt [options]
//   -size N    image width = height (power of 2, 64..512); overrides the scene file
//   -spp N     samples per pixel (1, 2, 4, 8, 16 or 32); overrides the scene file
//   -fixed     run only the 16-bit chip model      -float   run only the double-precision reference
//   -lfsr32    32-bit random generator (default: 16-bit Galois, taps 0x100B, as in the docs)
//   -linear    write raw chip output (no square-root brightness curve on the host)
//   -seed N    random generator start value (default 1)
//   -o NAME    output prefix (default "out")
// Writes NAME_fixed.bmp, NAME_float.bmp, NAME_diff.bmp (|fixed - float| x 8) and prints a report.
//
// What the sim models
//  * Host (laptop) part: reads the scene file, moves the scene so the camera is at x = 0, y = 0,
//    and packs everything into the 512 x 16-bit SRAM image. Chip part: reads only that SRAM image.
//    The chip part reads SRAM words when the RTU would read them, so every read is counted.
//    Startup: when RENDER arrives, the RTU reads the 17 header words once into header registers
//    (2 cycles per word, once per render, not counted per segment). The header is never read again.
//    Winner (closest hit) after the search: the RTU reads w0-w2 (colour, material); a triangle also its
//    edges w3-w8. The sphere test of the current best hit leaves its offset, half chord, radius and
//    flip bit (ray starts inside) in registers, so the winner's test is not run again. A triangle keeps
//    its flip bit (back side) and its K.
//  * Number formats: POS = Q9.7 (raw = value x 128, range +-256). DIR = Q2.14 (raw = value x 16384,
//    range +-2). Every add, multiply, shift and divide clamps to 16 bits. Colours are integers 0..255.
//  * CORDIC ops (MAG, DIV, RECP, SQRT, COS) return exactly rounded results. A real CORDIC adds 1-2 LSB.
//  * The float reference runs the same flow on the same SRAM image and the same random bits, with double math.
//  * Cycle estimate = macro-op count x cycles per macro-op (COST). Decode Unit: all six operands go into
//    R0-R5 in 1 cycle, R0-R2 are wired to the result, scalar macro-ops go straight to their unit.
//    Vector macro-op cycles follow one rule (render pipeline page, Timing C): cycle 1 accept + load;
//    one micro-op issues per cycle from cycle 2, in ROM order; a micro-op issued in cycle k on a unit
//    with L cycles is done in cycle k + L; a barrier micro-op issues the cycle after the last done;
//    a CORDIC micro-op waits until the cycle after the CORDIC's last done; the macro-op ends
//    2 cycles after its last done (1 cycle to see that nothing runs, 1 cycle reply).
//    Unit cycles: ALU and multiplier 1 (assumption); CORDIC (docs cordic.md, 16 turns, worst case):
//    divide and 1/x 17, cos 18, length 19, square root 23. Scalar macro-op = unit cycles + 2.
//    Controller time between macro-ops is not counted. Clock 25 MHz (assumption).
//  * Random numbers: 16-bit Galois LFSR, taps 0x100B, starts at 1 (docs rng.md). Each draw shifts it
//    16 times, so two draws share no bits (assumption: the docs shift once per request).
//  * UART: the I/O Unit sends one pixel while the RTU renders the next one. PIXEL message (docs
//    uart_frame.md) = 4 bytes (0x00, R, G, B), 10 bits each (start, 8 data, stop) = 40 bits. A data byte
//    equal to 0x00 or 0x03 is sent after a DLE byte (0x03): 10 more bits (escape rule assumed).
//    The RTU starts a pixel only when the Accumulator is free, so the I/O Unit takes pixel i + 1 at
//    take(i) + max(render time of pixel i + 1, UART time of pixel i).
//
// Chip behaviour (fixed in hardware)
//  * Camera at (0, 0, z). Ground at z = 0, always on. Checker colour B where bit 9 of hit x XOR hit y is 1
//    (bit 9 of a POS raw value = 4 units, so squares are 4 x 4).
//  * Ground divide clamped (t = 0x7FFF = 255.99) means the ground is too far away: the path ends at the sky.
//  * 8 bounces. A path that hits a surface on segment 9 gives a black sample.
//  * Materials (object w2 bits 1:0): 00 matte, 01 mirror (perfect), 10 glass (spheres only, IOR 1.5), 11 glow.
//  * Attenuation: 8 bits per colour, starts at 255, att = att x (c + 1) >> 8 at every surface.
//  * Sample: 12 bits per colour. Sky: (att + 1) x L >> 8. Glow: ((att + 1) x c >> 8) x strength >> 10.
//  * Pixel = (sum of s samples) >> log2 s, clamped to 255. s = 1, 2, 4, 8, 16 or 32 (17-bit accumulator).
//  * Matte bounce: new D = resize(n + random length-1 arrow). No loop. The random arrow uses
//    z = 8 random bits, heading phi = 8 random bits x 90 deg, and 2 random sign bits that pick the quarter turn.
//    cos(phi) and sin(phi) = cos(phi - 90 deg) are two M_COS calls. phi stays in 0..90 deg, so both
//    CORDIC inputs stay inside the CORDIC range (+-99.8 deg).
//
// SRAM layout (w = word address). Header vectors are x, y, z; object vectors are z, y, x (docs order).
//   w0-2 F (DIR)   w3-5 R   w6-8 U
//   w9-11  sky:    horizon R|G, horizon B|top R, top G|top B          (8 bits each, high byte first)
//   w12-14 ground: A R|G, A B|B R, B G|B B                            (checker colours A and B)
//   w15    settings: bits 7:3 bounding-volume count (0..16), bits 2:0 log2 samples (0..5)
//   w16    camera z (POS), 0 < z < 256
//   (all 17 header words are read once per render into header registers)
//   then 5 words per bounding volume (BV, a sphere around nearby objects):
//        w0 first object address [15:7] | object count [6:0], w1 radius, w2-w4 centre z, y, x
//   then objects (docs/encoding/scene.md): sphere 7 words, triangle 12 words.
#define _CRT_SECURE_NO_WARNINGS
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
using namespace std;

constexpr int PF = 7, DF = 14, MEMW = 512, BOUNCES = 8, MAXSPP = 32;
constexpr int HDR = 17;                          // first bounding-volume record
constexpr int MAXBV = 16;                        // bounding volumes: count field w15 bits 7:3
constexpr int W_F = 0, W_R = 3, W_U = 6, W_SKY = 9, W_GND = 12, W_SET = 15, W_CAMZ = 16;
enum { MAT_MATTE, MAT_MIRROR, MAT_GLASS, MAT_GLOW };
enum { K_SKY, K_GROUND, K_OBJ };

// ------------------------------------------------------------------ statistics
enum { C_ALU, C_ALUC, C_MUL, C_DIV, C_SQRT, C_MAG, C_COS, C_VADD, C_SCAL, C_DOT, C_CROSS, C_NORM, C_SNORM, C_VMUL, C_SRAM, C_VSHIFT, NC };
const char* CNAME[NC] = {"add/sub/compare (two values)", "compare with 0 or constant", "M_MUL", "M_DIV", "M_SQRT", "M_MAG",
                         "M_COS", "M_VADD / M_VSUB", "M_SCAL_VEC", "M_DOT", "M_CROSS", "M_NORM", "M_SPHERE_NORM", "M_VMUL",
                         "SRAM word read", "shift by K (request path)"};
// Cycles per macro-op with the Decode Unit (rule in the header comment; scalar ops bypass R0-R7)
const int COST[NC] = {3, 3, 3, 19, 25, 21, 20, 7, 7, 11, 14, 65, 57, 7, 2, 0};
constexpr double CLK_HZ = 25e6;
static double cycles_now();
// UART model (see the header comment). One per baud rate.
struct UartSim {
  double baud, take = 0, prev_u = 0; bool first = true; uint64_t limited = 0, pixels = 0, bits = 0;
  explicit UartSim(double b) : baud(b) {}
  void pixel(double render_s, const uint8_t* rgb) {
    int nb = 40;
    for (int k = 0; k < 3; k++) if (rgb[k] == 0x00 || rgb[k] == 0x03) nb += 10;  // DLE escape
    double u = nb / baud;
    if (first) { take = render_s; first = false; }
    else { if (prev_u > render_s) limited++; take += max(render_s, prev_u); }
    prev_u = u; pixels++; bits += nb;
  }
  double frame() const { return take + prev_u; }
};
vector<UartSim>* g_uart = nullptr;
struct Stats {
  uint64_t op[NC], draws, segs, samples, bvt, bvpass, spht, trit, skyend, glowend, limit, matte, gndhit, mirror, glassn,
      gclamp, nearzero, sat, satcrit, cordic_out, acc_over, tri2, tri3, tri4, hdr_reads, flipdiff;
} st;
bool g_crit = false;  // set while computing values that should never clamp (ray, hit point, out-arrow)

static int msb(int v) { int m = -1; while (v > 0) { m++; v >>= 1; } return m; }

// ------------------------------------------------------------------ number models
struct Fix {  // 16-bit saturating fixed point, held in int32
  using S = int32_t;
  static S sat(int64_t v) {
    if (v > 32767 || v < -32768) { st.sat++; st.satcrit += g_crit; return v > 0 ? 32767 : -32768; }
    return (S)v;
  }
  static S c(double x, int f) { return sat(llround(x * (1 << f))); }
  static S q(int raw, int) { return raw; }
  static int raw(S a, int) { return a; }
  static int rawfloor(S a, int) { return a; }
  static S reinterp(S a, int) { return a; }  // same bits, read as Q2.14
  static S add(S a, S b) { return sat((int64_t)a + b); }
  static S sub(S a, S b) { return sat((int64_t)a - b); }
  static S inv(S a, bool f) { return f ? ~a : a; }  // XOR with all ones in the request path: -a - 1 LSB
  static S mul(S a, S b, int sh) { return sat(((int64_t)a * b + (1LL << (sh - 1))) >> sh); }
  static S shift(S a, int k) {  // k > 0: divide by 2^k (rounded); k < 0: multiply by 2^-k (clamped)
    return k > 0 ? (S)((a + (1 << (k - 1))) >> k) : k < 0 ? sat((int64_t)a * (1LL << -k)) : a;
  }
  static S div(S a, S b, int sh) {  // (a << sh) / b, rounded to nearest
    if (b == 0) return sat(a >= 0 ? 1LL << 40 : -(1LL << 40));
    int64_t n = (int64_t)a * (1LL << sh), d = b;
    if (d < 0) { n = -n; d = -d; }
    return sat(n >= 0 ? (n + d / 2) / d : -((-n + d / 2) / d));
  }
  static int64_t isqrt(int64_t v) {  // rounded integer square root
    if (v <= 0) return 0;
    int64_t r = (int64_t)std::sqrt((double)v);
    while (r * r > v) r--;
    while ((r + 1) * (r + 1) <= v) r++;
    return (v - r * r > r) ? r + 1 : r;
  }
  static S sqrtv(S a, int f) { return a > 0 ? sat(isqrt((int64_t)a << f)) : 0; }
  static S mag(S a, S b) { return sat(isqrt((int64_t)a * a + (int64_t)b * b)); }
  static S cosv(S a) { return sat(llround(std::cos(a / 16384.0) * 16384)); }  // angle in radians, DIR
  static double rad(S a) { return a / 16384.0; }
};
struct Flt {  // double-precision reference with the same interface
  using S = double;
  static S c(double x, int) { return x; }
  static S q(int raw, int f) { return ldexp((double)raw, -f); }
  static int raw(S a, int f) { return (int)llround(ldexp(a, f)); }
  static int rawfloor(S a, int f) { return (int)floor(ldexp(a, f)); }
  static S reinterp(S a, int f) { return ldexp(a, f - DF); }
  static S add(S a, S b) { return a + b; }
  static S sub(S a, S b) { return a - b; }
  static S inv(S a, bool f) { return f ? -a : a; }
  static S mul(S a, S b, int) { return a * b; }
  static S shift(S a, int k) { return ldexp(a, -k); }
  static S div(S a, S b, int) { return b == 0 ? (a >= 0 ? 1e30 : -1e30) : a / b; }
  static S sqrtv(S a, int) { return a > 0 ? std::sqrt(a) : 0; }
  static S mag(S a, S b) { return hypot(a, b); }
  static S cosv(S a) { return std::cos(a); }
  static double rad(S a) { return a; }
};

// ------------------------------------------------------------------ random numbers
struct Lfsr {
  bool w32; uint32_t s = 1;
  Lfsr(bool w, uint32_t seed) : w32(w), s(w ? (seed ? seed : 1) : (seed & 0xFFFF ? seed & 0xFFFF : 1)) {}
  int draw() {  // 16 steps per number so consecutive numbers do not share bits
    st.draws++;
    for (int i = 0; i < 16; i++) {
      if (w32) { uint32_t m = s >> 31; s <<= 1; if (m) s ^= 0x00400007u; }
      else { uint32_t m = (s >> 15) & 1; s = (s << 1) & 0xFFFF; if (m) s ^= 0x100B; }
    }
    return (int)(s & 0xFFFF);
  }
};

struct Opt { int size = 0, spp = 0; uint32_t seed = 1; bool lfsr32 = false, gamma = true; };

// ------------------------------------------------------------------ chip model
template <class M> struct Chip {
  using S = typename M::S;
  struct Vec { S x, y, z; };
  struct Obj { int type = 0, mat = 0, rgb[3] = {0, 0, 0}, strength = 0, k = 0; Vec a{}, b{}, c{}; S r{}; };
  // Values the test of the current best hit leaves in registers, so the winner needs no second test.
  // Sphere: offset, half chord, radius (all size-scaled) and flip = ray starts inside (glass).
  // Triangle: flip = ray hits the back side (det < 0) and k = its size shift K.
  struct Keep { Vec ps{}; S hs{}, rs{}; bool flip = false; int k = 0; };
  struct Hit { int kind; int addr; S t; Keep keep; };

  const vector<uint16_t>& mem; int W, spp, log2s, ng; Lfsr rng;
  S ZERO, ONE_D, TMIN, EPS, NEAR225, BIG, HALF_PI;
  // Header registers, loaded once at startup: F, R, U (DIR), camera z (POS), sky and ground colours, settings
  Vec F{}, R{}, U{}; S camz{}; int sky_h[3], sky_t[3], gnd_a[3], gnd_b[3];

  // ---- macro-ops (each call = one request to Decode)
  static S add(S a, S b) { st.op[C_ALU]++; return M::add(a, b); }
  static S sub(S a, S b) { st.op[C_ALU]++; return M::sub(a, b); }
  static bool lt(S a, S b) { st.op[C_ALU]++; return a < b; }
  static bool ltc(S a, S b) { st.op[C_ALUC]++; return a < b; }  // one side is 0 or a constant
  static S mul(S a, S b, int sh) { st.op[C_MUL]++; return M::mul(a, b, sh); }
  static S div(S a, S b, int sh) { st.op[C_DIV]++; return M::div(a, b, sh); }
  static S sqrt(S a, int f) { st.op[C_SQRT]++; return M::sqrtv(a, f); }
  static S cosv(S a) {
    st.op[C_COS]++;
    if (fabs(M::rad(a)) > 1.7433) st.cordic_out++;  // outside the CORDIC range: the real chip returns garbage
    return M::cosv(a);
  }
  static Vec vadd(Vec a, Vec b) { st.op[C_VADD]++; return {M::add(a.x, b.x), M::add(a.y, b.y), M::add(a.z, b.z)}; }
  static Vec vsub(Vec a, Vec b) { st.op[C_VADD]++; return {M::sub(a.x, b.x), M::sub(a.y, b.y), M::sub(a.z, b.z)}; }
  static Vec scal(S s, Vec v, int sh) { st.op[C_SCAL]++; return {M::mul(s, v.x, sh), M::mul(s, v.y, sh), M::mul(s, v.z, sh)}; }
  static S dot(Vec a, Vec b, int sh) {
    st.op[C_DOT]++;
    return M::add(M::add(M::mul(a.x, b.x, sh), M::mul(a.y, b.y, sh)), M::mul(a.z, b.z, sh));
  }
  static Vec cross(Vec a, Vec b, int sh) {
    st.op[C_CROSS]++;
    return {M::sub(M::mul(a.y, b.z, sh), M::mul(a.z, b.y, sh)), M::sub(M::mul(a.z, b.x, sh), M::mul(a.x, b.z, sh)),
            M::sub(M::mul(a.x, b.y, sh), M::mul(a.y, b.x, sh))};
  }
  static Vec vshift(Vec v, int k) {  // shift by K: barrel shifter in the request path, no macro-op
    if (k) st.op[C_VSHIFT]++;
    return {M::shift(v.x, k), M::shift(v.y, k), M::shift(v.z, k)};
  }
  // M_NORM: resize to length 1. The request path first shifts so the largest part is 0.5..1 read as DIR
  // (leading-one finder), then Decode runs MAG, MAG, RECP and 3 MUL.
  Vec normalize(Vec v, int f) {
    st.op[C_NORM]++;
    int m = max({abs(M::raw(v.x, f)), abs(M::raw(v.y, f)), abs(M::raw(v.z, f))});
    int k = m ? msb(m) - (DF - 1) : 0;
    Vec w = {M::shift(M::reinterp(v.x, f), k), M::shift(M::reinterp(v.y, f), k), M::shift(M::reinterp(v.z, f), k)};
    S inv = M::div(ONE_D, M::mag(M::mag(w.x, w.y), w.z), DF);
    return {M::mul(inv, w.x, DF), M::mul(inv, w.y, DF), M::mul(inv, w.z, DF)};
  }
  // M_VMUL on colours: part-by-part multiply, rounded, 3 MUL on the shared multiplier
  static void vmul(const int a[3], const int b[3], int sh, int out[3]) {
    st.op[C_VMUL]++;
    for (int k = 0; k < 3; k++) out[k] = (a[k] * b[k] + (1 << (sh - 1))) >> sh;
  }

  // ---- SRAM access
  int rd(int a) { st.op[C_SRAM]++; return (int16_t)mem[a]; }
  unsigned rdu(int a) { st.op[C_SRAM]++; return mem[a]; }
  void unpack2(int a, int c1[3], int c2[3]) const {  // two colours packed in three header words (startup only)
    unsigned w0 = mem[a], w1 = mem[a + 1], w2 = mem[a + 2];
    c1[0] = w0 >> 8; c1[1] = w0 & 255; c1[2] = w1 >> 8; c2[0] = w1 & 255; c2[1] = w2 >> 8; c2[2] = w2 & 255;
  }
  static int k_sphere(int r_raw) { return r_raw > 0 ? msb(r_raw) - 10 : 0; }  // radius -> 8..16
  static int k_tri(int m_raw) { return m_raw > 0 ? msb(m_raw) - 9 : 0; }      // largest edge part -> 4..8

  // Winner only: colour, material and strength (w0-w2).
  Obj read_head(int addr) {
    Obj ob; unsigned w0 = rdu(addr), w1 = rdu(addr + 1), w2 = rdu(addr + 2);
    ob.type = w0 & 1; ob.rgb[0] = w1 >> 8; ob.rgb[1] = w1 & 255; ob.rgb[2] = w0 >> 8; ob.mat = w2 & 3; ob.strength = w2 >> 2;
    return ob;
  }
  // Search: test words only (w0 for the type bit, then w3..).
  Obj read_obj(int addr) {
    Obj ob; unsigned w0 = rdu(addr);
    ob.type = w0 & 1; ob.rgb[2] = w0 >> 8;
    if (ob.type) {  // sphere: w3 R, w4 Z, w5 Y, w6 X
      int rr = rd(addr + 3);
      ob.r = M::q(rr, PF); ob.k = k_sphere(rr);
      ob.a = {M::q(rd(addr + 6), PF), M::q(rd(addr + 5), PF), M::q(rd(addr + 4), PF)};
    } else {        // triangle: w3-5 edge 2 z,y,x | w6-8 edge 1 z,y,x | w9-11 corner v0 z,y,x
      int raw[9], m = 0;  // m = largest edge part, picks the size scaling K
      for (int i = 0; i < 9; i++) { raw[i] = rd(addr + 3 + i); if (i < 6) m = max(m, abs(raw[i])); }
      ob.c = {M::q(raw[2], PF), M::q(raw[1], PF), M::q(raw[0], PF)};
      ob.b = {M::q(raw[5], PF), M::q(raw[4], PF), M::q(raw[3], PF)};
      ob.a = {M::q(raw[8], PF), M::q(raw[7], PF), M::q(raw[6], PF)};
      ob.k = k_tri(m);
    }
    return ob;
  }

  Chip(const vector<uint16_t>& m, const Opt& op, int size) : mem(m), W(size), rng(op.lfsr32, op.seed) {
    ZERO = M::c(0, PF); ONE_D = M::c(1.0, DF); TMIN = M::c(2.0 / 128, PF); EPS = M::c(4.0 / 128, PF);
    NEAR225 = M::c(225.0, PF); BIG = M::q(32767, PF); HALF_PI = M::c(3.14159265358979323846 / 2, DF);
    // Startup: 17 header words, once per render, into header registers. Not counted per segment.
    st.hdr_reads += HDR;
    auto v3 = [&](int a) { return Vec{M::q((int16_t)mem[a], DF), M::q((int16_t)mem[a + 1], DF), M::q((int16_t)mem[a + 2], DF)}; };
    F = v3(W_F); R = v3(W_R); U = v3(W_U);
    unpack2(W_SKY, sky_h, sky_t); unpack2(W_GND, gnd_a, gnd_b);
    unsigned set = mem[W_SET];
    ng = (set >> 3) & 31; log2s = set & 7; spp = 1 << log2s;   // ng: number of bounding volumes
    camz = M::q((int16_t)mem[W_CAMZ], PF);
  }

  // ---- tests
  bool bv_test(Vec org, Vec d, Vec c, S r, int k) {
    st.bvt++;
    Vec oc = vsub(c, org);
    S along = dot(oc, d, DF);
    S rs = M::shift(r, k), r2 = mul(rs, rs, PF);
    Vec ocs = vshift(oc, k);
    if (lt(dot(ocs, ocs, PF), r2)) return true;                          // ray starts inside the bounding volume
    if (ltc(along, ZERO)) return false;                                   // bounding volume is behind
    Vec ps = vshift(vsub(scal(along, d, DF), oc), k);
    return lt(dot(ps, ps, PF), r2);
  }
  bool sphere_test(Vec org, Vec d, const Obj& ob, S& t, Keep& keep) {
    st.spht++;
    Vec oc = vsub(ob.a, org);
    S along = dot(oc, d, DF);                              // how far along to be level with the centre
    Vec ps = vshift(vsub(scal(along, d, DF), oc), ob.k);   // closest point - centre, size scaled
    S rs = M::shift(ob.r, ob.k), r2 = mul(rs, rs, PF);
    S pp = dot(ps, ps, PF);
    if (!lt(pp, r2)) return false;
    S hs = sqrt(sub(r2, pp), PF);                          // half chord (scaled)
    S h = M::shift(hs, -ob.k);
    bool inside = false; S t0 = sub(along, h);
    if (!ltc(TMIN, t0)) { t0 = add(along, h); inside = true; if (!ltc(TMIN, t0)) return false; }
    t = t0;
    keep = {ps, hs, rs, inside};                           // stays in registers if this becomes the best hit
    return true;
  }
  // Winner sphere: out-arrow from the kept values, no second test.
  // (closest point - centre -/+ half chord x direction) = hit point - centre, length r_s; / r_s gives length 1.
  Vec sphere_n(const Keep& k, Vec d) {
    g_crit = true;
    Vec h = scal(k.hs, d, DF);
    Vec hc = k.flip ? vadd(k.ps, h) : vsub(k.ps, h);
    st.op[C_SNORM]++; Vec n = {M::div(hc.x, k.rs, DF), M::div(hc.y, k.rs, DF), M::div(hc.z, k.rs, DF)};
    if (k.flip) n = vsub({ZERO, ZERO, ZERO}, n);           // ray inside the glass: n faces the ray
    g_crit = false;
    return n;
  }
  bool tri_test(Vec org, Vec d, const Obj& ob, S& t, Keep& keep) {
    st.trit++;
    Vec tc = vsub(ob.a, org);                              // start -> corner v0
    S along = dot(tc, d, DF);
    Vec ts = vshift(vsub(scal(along, d, DF), tc), ob.k);   // slid start - v0, size scaled
    if (ltc(NEAR225, dot(ts, ts, PF))) return false;        // ray passes > 15 (scaled) from v0
    st.tri2++;
    st.op[C_SRAM] += 6;                                    // 7 scratch registers cannot hold the edges: read e2, e1 again
    Vec e1 = vshift(ob.b, ob.k), e2 = vshift(ob.c, ob.k);
    Vec P = cross(d, e2, DF);
    S det = dot(e1, P, PF), un = dot(ts, P, PF);
    bool flip = ltc(det, ZERO);
    if (flip) { det = sub(ZERO, det); un = sub(ZERO, un); }
    if (!ltc(ZERO, det) || ltc(un, ZERO) || lt(det, un)) return false;
    st.tri3++;
    st.op[C_SRAM] += 3;                                    // read e1 again
    Vec Q = cross(ts, e1, PF);
    S vn = dot(d, Q, DF);
    if (flip) vn = sub(ZERO, vn);
    if (ltc(vn, ZERO) || lt(det, add(un, vn))) return false;
    st.tri4++;
    st.op[C_SRAM] += 6;                                    // read e1, e2 again
    S u = div(un, det, DF), v = div(vn, det, DF);          // how far along edge 1 and edge 2 (DIR)
    S tt = add(add(along, mul(u, dot(ob.b, d, DF), DF)), mul(v, dot(ob.c, d, DF), DF));
    if (!ltc(TMIN, tt)) return false;
    t = tt;
    keep.flip = flip; keep.k = ob.k;                       // back side (det < 0) and K, kept with the best hit
    return true;
  }
  // Winner triangle: read e2, e1 (w3-w8) into the request fields of M_CROSS, shifted by the kept K.
  // The RTU writes each edge word into u or v; the kept flip bit picks which:
  //   front side (flip 0): e1 -> u, e2 -> v, so u x v = e1 x e2
  //   back side  (flip 1): e2 -> u, e1 -> v, so u x v = e2 x e1 = -(e1 x e2)
  // Then n = resize(u x v) always faces the ray. No second test, no n . D check.
  Vec tri_n(int addr, const Keep& kp, Vec d) {
    int raw[6];
    for (int i = 0; i < 6; i++) raw[i] = rd(addr + 3 + i);   // w3-w5 = e2 z, y, x; w6-w8 = e1 z, y, x
    bool back = kp.flip; int k = kp.k;
    Vec e2 = vshift({M::q(raw[2], PF), M::q(raw[1], PF), M::q(raw[0], PF)}, k);
    Vec e1 = vshift({M::q(raw[5], PF), M::q(raw[4], PF), M::q(raw[3], PF)}, k);
    g_crit = true;
    Vec n = normalize(back ? cross(e2, e1, PF) : cross(e1, e2, PF), PF);
    g_crit = false;
#ifdef FLIPCHECK  // compare with the old rule (flip when n . D > 0); op counts restored
    { uint64_t save[NC]; for (int i = 0; i < NC; i++) save[i] = st.op[i];
      Vec c = normalize(cross(e1, e2, PF), PF);
      S dd = M::add(M::add(M::mul(c.x, d.x, DF), M::mul(c.y, d.y, DF)), M::mul(c.z, d.z, DF));
      if ((ZERO < dd) != back) st.flipdiff++;
      for (int i = 0; i < NC; i++) st.op[i] = save[i]; }
#else
    (void)d;
#endif
    return n;
  }
  // One segment: bounding-volume loop, object loop, closest hit, then the ground if nothing was hit.
  Hit trace(Vec org, Vec d) {
    st.segs++;
    Hit h{K_SKY, -1, BIG, {}}; S t{}; Keep k;
    for (int g = 0; g < ng; g++) {
      int a = HDR + 5 * g, rr = rd(a + 1);                                 // BV record w1-w4: radius, centre
      Vec c = {M::q(rd(a + 4), PF), M::q(rd(a + 3), PF), M::q(rd(a + 2), PF)};
      if (!bv_test(org, d, c, M::q(rr, PF), k_sphere(rr))) continue;
      unsigned w0 = rdu(a); st.bvpass++;                                   // w0 only if the BV is reached
      for (int i = 0, oa = (int)(w0 >> 7); i < (int)(w0 & 127); i++) {
        Obj ob = read_obj(oa);
        bool hit = ob.type ? sphere_test(org, d, ob, t, k) : tri_test(org, d, ob, t, k);
        if (hit && lt(t, h.t)) h = {K_OBJ, oa, t, k};   // best t, best address and the kept test values
        oa += ob.type ? 7 : 12;
      }
    }
    if (h.kind == K_SKY && ltc(d.z, ZERO)) {         // nothing hit and the ray points down: test the ground
      S tg = div(M::inv(org.z, true), d.z, DF);     // t = -O_z / D_z; -O_z = XOR in the request path (-a - 1 step)
      if (tg >= BIG) { st.gclamp++; return h; }      // divide clamped (t = 0x7FFF): 16-input gate, no macro-op -> sky
      h = {K_GROUND, -1, tg, {}};
    }
    return h;
  }

  // ---- colour (integers, same in both models)
  void sky_sample(Vec d, const int att[3], int out[3]) {
    const int *hz = sky_h, *top = sky_t;           // header registers
    int f = max(M::raw(d.z, DF), 0);              // D_z below 0 uses 0 (sign-bit gate on the request field)
    st.op[C_VADD] += 2; st.op[C_SCAL]++;          // L = horizon + (top - horizon) x D_z >> 14
    int L[3], a1[3];
    for (int k = 0; k < 3; k++) { L[k] = hz[k] + (((top[k] - hz[k]) * f + 8192) >> 14); a1[k] = att[k] + 1; }
    vmul(a1, L, 8, out);                          // sample = (att + 1) x L >> 8, 0..255
  }
  void glow_sample(const Obj& ob, const int att[3], int out[3]) {
    int a1[3] = {att[0] + 1, att[1] + 1, att[2] + 1}, tmp[3];
    vmul(a1, ob.rgb, 8, tmp);                     // (att + 1) x c >> 8
    st.op[C_SCAL]++;                              // x strength (Q4.10) >> 10: 0..4080
    for (int k = 0; k < 3; k++) out[k] = (tmp[k] * ob.strength + 512) >> 10;
  }

  // Random length-1 arrow, no loop. 8 bits z, 8 bits heading, 2 sign bits.
  Vec rand_unit() {
    int d1 = rng.draw(), d2 = rng.draw();
    int z8 = max(-127, (int)(int8_t)(d1 >> 8));  // -127..127 -> z = -0.992..0.992
    int w8 = d1 & 255;                           // 0..255 -> w = 0..0.996
    bool fx = d2 & 1, fy = (d2 >> 1) & 1;        // which quarter turn: sign of x, sign of y
    S z = M::q(z8 * 128, DF);
    S phi = mul(M::q(w8 * 64, DF), HALF_PI, DF);         // phi = w x pi/2: 0 .. 89.6 deg (radians, DIR)
    S s = sqrt(sub(ONE_D, mul(z, z, DF)), DF);           // circle radius at height z: sqrt(1 - z^2)
    S c = cosv(phi), sn = cosv(sub(phi, HALF_PI));       // cos(phi); cos(phi - 90 deg) = sin(phi)
    Vec r = scal(s, {M::inv(c, fx), M::inv(sn, fy), ZERO}, DF);  // (s cos, s sin); sign flips are XOR in the request path
    r.z = z;                                             // z goes straight from the LFSR bits
    return r;
  }
  Vec matte_dir(Vec n) {
    Vec s = vadd(n, rand_unit());
    if (M::raw(s.x, DF) == 0 && M::raw(s.y, DF) == 0 && M::raw(s.z, DF) == 0) { st.nearzero++; return n; }  // leading-one finder sees 0
    return normalize(s, DF);
  }

  // Glass sphere, IOR 1.5: reflect or bend. n faces the incoming ray.
  // Returns true if the ray bends through the surface (then the new start goes to the far side).
  bool glass(Vec& d, Vec n, bool from_inside) {
    S eta = from_inside ? M::c(1.5, DF) : M::c(2.0 / 3, DF);                // 1.5 going out, 0.667 going in
    S c = sub(ZERO, dot(d, n, DF));                                          // cos of the incoming angle
    S k = sub(ONE_D, mul(eta, mul(eta, sub(ONE_D, mul(c, c, DF)), DF), DF));  // cos^2 of the outgoing angle
    S x = sub(ONE_D, c), x2 = mul(x, x, DF), x5 = mul(mul(x2, x2, DF), x, DF);
    S refl = add(M::c(0.04, DF), mul(M::c(0.96, DF), x5, DF));             // reflect share: 0.04 + 0.96 (1 - c)^5
    if (ltc(k, ZERO) || lt(M::q((rng.draw() & 0xFF) << 6, DF), refl)) {    // cannot get out, or 8 random bits chose reflect
      d = vadd(d, scal(add(c, c), n, DF));
      return false;
    }
    d = normalize(vadd(scal(eta, d, DF), scal(sub(mul(eta, c, DF), sqrt(k, DF)), n, DF)), DF);
    return true;
  }

  // One sample: follow the path, return the sample colour (0..4080 per colour).
  void path(Vec org, Vec d, int out[3]) {
    int att[3] = {255, 255, 255};
    out[0] = out[1] = out[2] = 0;
    for (int b = 0;; b++) {
      Hit h = trace(org, d);
      if (h.kind == K_SKY) { st.skyend++; sky_sample(d, att, out); return; }
      Obj ob;
      if (h.kind == K_OBJ) {
        ob = read_head(h.addr);                  // winner: w0-w2 only
        if (ob.mat == MAT_GLOW) { st.glowend++; glow_sample(ob, att, out); return; }
      }
      if (b >= BOUNCES) { st.limit++; return; }  // bounce limit: black
      g_crit = true; Vec hp = vadd(org, scal(h.t, d, DF)); g_crit = false;
      Vec n; int col[3]; bool from_inside = false;
      if (h.kind == K_GROUND) {
        st.gndhit++;
        bool odd = ((M::rawfloor(hp.x, PF) ^ M::rawfloor(hp.y, PF)) >> 9) & 1;  // checker: bit 9 of x XOR y
        for (int k = 0; k < 3; k++) col[k] = odd ? gnd_b[k] : gnd_a[k];  // header registers
        n = {ZERO, ZERO, ONE_D};
      } else {
        if (ob.type) { n = sphere_n(h.keep, d); from_inside = h.keep.flip; }
        else n = tri_n(h.addr, h.keep, d);
        for (int k = 0; k < 3; k++) col[k] = ob.rgb[k];
      }
      int c1[3] = {col[0] + 1, col[1] + 1, col[2] + 1};
      vmul(att, c1, 8, att);                     // att = att x (c + 1) >> 8
      bool through = false;
      if (h.kind == K_OBJ && ob.mat == MAT_GLASS && ob.type) {
        st.glassn++; through = glass(d, n, from_inside);
      } else if (h.kind == K_OBJ && ob.mat == MAT_MIRROR) {
        st.mirror++;
        S dn = dot(d, n, DF);
        d = vsub(d, scal(add(dn, dn), n, DF));   // D - 2 (D . n) n
      } else {
        st.matte++; d = matte_dir(n);            // matte objects and ground
      }
      g_crit = true; org = through ? vsub(hp, scal(EPS, n, DF)) : vadd(hp, scal(EPS, n, DF)); g_crit = false;  // push off
    }
  }

  vector<uint8_t> render() {
    vector<uint8_t> img((size_t)W * W * 3);
    int jb = 15 - msb(W), half = W / 2, jm = (1 << jb) - 1;  // 512 x 512: 6 random bits below the pixel bits
    for (int j = 0; j < W; j++)
      for (int i = 0; i < W; i++) {
        int sum[3] = {0, 0, 0}; double c0 = cycles_now();
        for (int s = 0; s < spp; s++) {
          int jx = rng.draw() & jm, jy = rng.draw() & jm;
          S a = M::q((i - half) * (1 << jb) + jx, DF);      // -1 (left) .. +1 (right)
          S b = M::q((half - 1 - j) * (1 << jb) + jy, DF);  // +1 (top) .. -1 (bottom)
          g_crit = true;
          Vec d = normalize(vadd(vadd(F, scal(a, R, DF)), scal(b, U, DF)), DF);
          g_crit = false;
          int out[3];
          path({ZERO, ZERO, camz}, d, out);            // F, R, U, camera z: header registers
          st.samples++;
          for (int k = 0; k < 3; k++) sum[k] += out[k];
        }
        for (int k = 0; k < 3; k++) {
          if (sum[k] >= 1 << 17) st.acc_over++;
          img[((size_t)j * W + i) * 3 + k] = (uint8_t)min(255, sum[k] >> log2s);
        }
        if (g_uart) for (auto& u : *g_uart) u.pixel((cycles_now() - c0) / CLK_HZ, &img[((size_t)j * W + i) * 3]);
      }
    return img;
  }
};

// ------------------------------------------------------------------ host: scene file -> SRAM image
struct HObj { bool sph; double p[9], r; int mat, rgb[3], bv; double strength; };
struct Scene {
  int size = 512, spp = 8, sky[6] = {235, 240, 255, 120, 170, 255}, gA[3] = {200, 200, 200}, gB[3] = {200, 200, 200};
  double cam[3] = {0, 0, 16}, yaw = 45, pitch = 0, fov = 90;
  vector<HObj> obj;
};
[[noreturn]] static void die(const string& m) { fprintf(stderr, "error: %s\n", m.c_str()); exit(1); }
static int q7(double v) { if (fabs(v) >= 255.99) die("value " + to_string(v) + " outside +-256"); return (int)llround(v * 128); }
static int q14(double v) { if (fabs(v) >= 1.9999) die("screen vector part outside +-2 (fov too wide?)"); return (int)llround(v * 16384); }

static Scene load_scene(const string& path) {
  ifstream f(path); if (!f) die("cannot open " + path);
  Scene sc; string line; int ln = 0;
  auto where = [&]() { return "line " + to_string(ln) + ": "; };
  auto mat_of = [&](const string& m) {
    if (m == "matte" || m == "diffuse") return (int)MAT_MATTE;
    if (m == "mirror") return (int)MAT_MIRROR;
    if (m == "glass") return (int)MAT_GLASS;
    if (m == "glow" || m == "emissive") return (int)MAT_GLOW;
    die(where() + "unknown material " + m);
  };
  auto add_tri = [&](const double* a, const double* b, const double* c, int mat, const int* rgb, double str, int g) {
    if (mat == MAT_GLASS) { fprintf(stderr, "%sglass is spheres only, using matte\n", where().c_str()); mat = MAT_MATTE; }
    HObj o{false, {a[0], a[1], a[2], b[0] - a[0], b[1] - a[1], b[2] - a[2], c[0] - a[0], c[1] - a[1], c[2] - a[2]}, 0, mat, {rgb[0], rgb[1], rgb[2]}, g, str};
    sc.obj.push_back(o);
  };
  auto rgb3 = [&](istringstream& s, int* c) {
    s >> c[0] >> c[1] >> c[2]; if (!s) die(where() + "expected R G B");
    for (int k = 0; k < 3; k++) if (c[k] < 0 || c[k] > 255) die(where() + "colour outside 0..255");
    double extra; if (s >> extra) die(where() + "too many numbers (old format? see the scene file comments)");
  };
  while (getline(f, line)) {
    ln++; line = line.substr(0, line.find('#'));
    istringstream s(line); string kw; if (!(s >> kw)) continue;
    auto tail = [&](int& mat, int* rgb, double& str, int& g) {  // material R G B [strength] [bounding volume]
      string m; s >> m >> rgb[0] >> rgb[1] >> rgb[2]; if (!s) die(where() + "bad material/colour");
      mat = mat_of(m); str = 0; g = 0; s >> str >> g; s.clear();
      if (str != 0 && mat != MAT_GLOW) { fprintf(stderr, "%sstrength is used by glow only, ignored\n", where().c_str()); str = 0; }
      if (mat == MAT_GLOW && (str < 0 || str > 15.99)) die(where() + "glow strength must be 0..15.99");
    };
    int mat, rgb[3], g; double str, v[12];
    if (kw == "image") s >> sc.size;
    else if (kw == "spp") s >> sc.spp;
    else if (kw == "camera") s >> sc.cam[0] >> sc.cam[1] >> sc.cam[2] >> sc.yaw >> sc.pitch >> sc.fov;
    else if (kw == "sky") { s >> sc.sky[0] >> sc.sky[1] >> sc.sky[2]; for (int k = 0; k < 3; k++) sc.sky[3 + k] = sc.sky[k]; s >> sc.sky[3] >> sc.sky[4] >> sc.sky[5]; }
    else if (kw == "ground") { rgb3(s, sc.gA); for (int k = 0; k < 3; k++) sc.gB[k] = sc.gA[k]; }
    else if (kw == "checker") rgb3(s, sc.gB);
    else if (kw == "bounces") die(where() + "'bounces' was removed: the chip always allows 8 bounces");
    else if (kw == "far") die(where() + "'far' was removed: the ground is sky when the divide clamps (t >= 256)");
    else if (kw == "sphere") {
      HObj o{true, {}, 0, 0, {}, 0, 0}; s >> o.p[0] >> o.p[1] >> o.p[2] >> o.r; tail(o.mat, o.rgb, o.strength, o.bv); sc.obj.push_back(o);
    } else if (kw == "tri") {
      for (int i = 0; i < 9; i++) s >> v[i];
      tail(mat, rgb, str, g); add_tri(v, v + 3, v + 6, mat, rgb, str, g);
    } else if (kw == "quad") {  // 4 corners in order -> 2 triangles
      for (int i = 0; i < 12; i++) s >> v[i];
      tail(mat, rgb, str, g); add_tri(v, v + 3, v + 6, mat, rgb, str, g); add_tri(v, v + 6, v + 9, mat, rgb, str, g);
    } else if (kw == "box") {  // axis-aligned box from 2 corners -> 12 triangles (host-side helper only)
      double a[3], b[3]; s >> a[0] >> a[1] >> a[2] >> b[0] >> b[1] >> b[2]; tail(mat, rgb, str, g);
      auto P = [&](int i, double* out) { out[0] = i & 1 ? b[0] : a[0]; out[1] = i & 2 ? b[1] : a[1]; out[2] = i & 4 ? b[2] : a[2]; };
      static const int face[6][4] = {{0, 1, 3, 2}, {4, 6, 7, 5}, {0, 4, 5, 1}, {2, 3, 7, 6}, {0, 2, 6, 4}, {1, 5, 7, 3}};
      for (auto& fc : face) { double c[4][3]; for (int i = 0; i < 4; i++) P(fc[i], c[i]); add_tri(c[0], c[1], c[2], mat, rgb, str, g); add_tri(c[0], c[2], c[3], mat, rgb, str, g); }
    } else die(where() + "unknown keyword " + kw);
  }
  return sc;
}

static vector<uint16_t> pack(Scene sc, int spp) {
  vector<uint16_t> m(MEMW, 0);
  auto put = [&](int a, int v) { if (a >= MEMW) die("scene does not fit in 512 words"); m[a] = (uint16_t)(v & 0xFFFF); };
  const double PI = 3.14159265358979323846;
  // camera must be at x = 0, y = 0: move every object by -camera x, -camera y (edges do not move)
  for (auto& o : sc.obj) { o.p[0] -= sc.cam[0]; o.p[1] -= sc.cam[1]; }
  if (sc.cam[2] <= 0) die("camera must be above the ground (z > 0)");
  if (sc.fov <= 0 || sc.fov > 90) die("field of view must be above 0 and at most 90 degrees (|R|, |U| <= 1 keeps F + aR + bU inside DIR)");
  double y = sc.yaw * PI / 180, p = sc.pitch * PI / 180, tf = tan(sc.fov * PI / 360);
  double F[3] = {cos(p) * cos(y), cos(p) * sin(y), sin(p)}, R[3] = {sin(y) * tf, -cos(y) * tf, 0},
         U[3] = {-sin(p) * cos(y) * tf, -sin(p) * sin(y) * tf, cos(p) * tf};
  for (int k = 0; k < 3; k++) { put(W_F + k, q14(F[k])); put(W_R + k, q14(R[k])); put(W_U + k, q14(U[k])); }
  auto rgb2 = [&](int a, const int* c1, const int* c2) { put(a, c1[0] << 8 | c1[1]); put(a + 1, c1[2] << 8 | c2[0]); put(a + 2, c2[1] << 8 | c2[2]); };
  rgb2(W_SKY, sc.sky, sc.sky + 3); rgb2(W_GND, sc.gA, sc.gB);
  int ng = 0; for (auto& o : sc.obj) ng = max(ng, o.bv + 1);
  if (ng > MAXBV) die("at most 16 bounding volumes");
  put(W_SET, ng << 3 | msb(spp));
  put(W_CAMZ, q7(sc.cam[2]));
  int a = HDR + 5 * ng;
  for (int g = 0; g < ng; g++) {  // bounding volume: sphere around every object with this BV number (+ margin)
    double lo[3] = {1e9, 1e9, 1e9}, hi[3] = {-1e9, -1e9, -1e9}, c[3], r = 0; int start = a, count = 0;
    auto pts = [&](const HObj& o, auto fn) {
      if (o.sph) fn(o.p, o.r);
      else { double q[3]; for (int i = 0; i < 3; i++) { for (int k = 0; k < 3; k++) q[k] = o.p[k] + (i == 1 ? o.p[3 + k] : i == 2 ? o.p[6 + k] : 0); fn(q, 0.0); } }
    };
    for (auto& o : sc.obj) if (o.bv == g) pts(o, [&](const double* q, double rr) { for (int k = 0; k < 3; k++) { lo[k] = min(lo[k], q[k] - rr); hi[k] = max(hi[k], q[k] + rr); } });
    for (int k = 0; k < 3; k++) c[k] = (lo[k] + hi[k]) / 2;
    for (auto& o : sc.obj) if (o.bv == g) pts(o, [&](const double* q, double rr) { r = max(r, hypot(hypot(q[0] - c[0], q[1] - c[1]), q[2] - c[2]) + rr); });
    if (lo[2] < -1e-9) fprintf(stderr, "warning: bounding volume %d goes below z = 0; the ground test assumes every object is at z >= 0\n", g);
    for (auto& o : sc.obj) {
      if (o.bv != g) continue;
      int str = o.mat == MAT_GLOW ? (int)llround(min(o.strength * 1024, 16383.0)) : 0;  // strength Q4.10
      put(a, o.rgb[2] << 8 | (g & 127) << 1 | (o.sph ? 1 : 0)); put(a + 1, o.rgb[0] << 8 | o.rgb[1]); put(a + 2, str << 2 | o.mat);
      if (o.sph) { put(a + 3, q7(o.r)); put(a + 4, q7(o.p[2])); put(a + 5, q7(o.p[1])); put(a + 6, q7(o.p[0])); a += 7; }
      else { for (int i = 0; i < 9; i++) put(a + 3 + i, q7(o.p[8 - i])); a += 12; }
      count++;
    }
    if (count > 127) die("more than 127 objects in a bounding volume");
    int b = HDR + 5 * g;
    put(b, start << 7 | count); put(b + 1, q7(r + 0.05)); put(b + 2, q7(c[2])); put(b + 3, q7(c[1])); put(b + 4, q7(c[0]));
  }
  printf("SRAM: %d of %d words used (header %d, bounding volumes %d, objects %d)\n", a, MEMW, HDR, 5 * ng, a - HDR - 5 * ng);
  double span = 0, reach = 0, cam[3] = {0, 0, sc.cam[2]};  // every ray start must be < 256 from every object point
  auto ext = [](const HObj& o) { return o.sph ? o.r : max(hypot(hypot(o.p[3], o.p[4]), o.p[5]), hypot(hypot(o.p[6], o.p[7]), o.p[8])); };
  auto dist = [](const double* u, const double* v) { return hypot(hypot(u[0] - v[0], u[1] - v[1]), u[2] - v[2]); };
  for (auto& o1 : sc.obj) {
    reach = max(reach, dist(o1.p, cam) + ext(o1));
    for (auto& o2 : sc.obj) span = max(span, dist(o1.p, o2.p) + ext(o1) + ext(o2));
  }
  if (span > 250 || reach > 250)
    fprintf(stderr, "warning: scene may break the 256-unit rule (object span %.0f, camera reach %.0f)\n", span, reach);
  return m;
}

// ------------------------------------------------------------------ output
static void write_bmp(const string& fn, const vector<uint8_t>& img, int W, bool gamma) {
  FILE* f = fopen(fn.c_str(), "wb"); if (!f) die("cannot write " + fn);
  int row = (W * 3 + 3) & ~3, size = 54 + row * W;
  uint8_t h[54] = {'B', 'M'};
  auto le = [&](int o, int v, int n) { for (int i = 0; i < n; i++) h[o + i] = (uint8_t)(v >> (8 * i)); };
  le(2, size, 4); le(10, 54, 4); le(14, 40, 4); le(18, W, 4); le(22, W, 4); le(26, 1, 2); le(28, 24, 2);
  fwrite(h, 1, 54, f);
  vector<uint8_t> line(row, 0);
  for (int j = W - 1; j >= 0; j--) {
    for (int i = 0; i < W; i++)
      for (int k = 0; k < 3; k++) {
        int v = img[((size_t)j * W + i) * 3 + k];
        line[i * 3 + 2 - k] = (uint8_t)(gamma ? llround(255 * std::sqrt(v / 255.0)) : v);  // BMP stores B,G,R
      }
    fwrite(line.data(), 1, row, f);
  }
  fclose(f);
}

static double cycles_now() { double c = 0; for (int i = 0; i < NC; i++) c += (double)st.op[i] * COST[i]; return c; }

static void report(int W, int spp) {
  double segs = (double)st.segs, cyc = cycles_now();
  printf("  startup: %llu header words read once per render (2 cycles each, not in the per-segment counts)\n",
         (unsigned long long)st.hdr_reads);
  printf("  samples %llu, segments %llu (%.3f per sample)\n", (unsigned long long)st.samples, (unsigned long long)st.segs, segs / st.samples);
  printf("  per segment: bounding-volume tests %.3f (reached %.3f), sphere tests %.3f, triangle tests %.3f\n", st.bvt / segs, st.bvpass / segs, st.spht / segs, st.trit / segs);
  printf("  triangle test stages reached per segment: 1: %.3f, 2: %.3f, 3: %.3f, 4: %.3f\n", st.trit / segs, st.tri2 / segs, st.tri3 / segs, st.tri4 / segs);
  printf("  path ends per segment: sky %.3f, glow %.3f, bounce limit %.3f\n", st.skyend / segs, st.glowend / segs, st.limit / segs);
  printf("  bounces per segment: matte %.3f (ground %.3f), mirror %.3f, glass %.3f\n", st.matte / segs, st.gndhit / segs, st.mirror / segs, st.glassn / segs);
  printf("  %-30s %9s %9s %9s\n", "macro-op", "count/seg", "cyc each", "cyc/seg");
  for (int i = 0; i < NC; i++) printf("  %-30s %9.3f %9d %9.1f\n", CNAME[i], st.op[i] / segs, COST[i], st.op[i] * COST[i] / segs);
  printf("  TOTAL cycles per segment (Decode Unit): %.1f\n", cyc / segs);
  double scale = 512.0 * 512.0 / ((double)W * W);
  printf("  512 x 512 frame at %d samples, 25 MHz, render only: %.1f s = %.2f min (no Controller time)\n",
         spp, cyc * scale / CLK_HZ, cyc * scale / CLK_HZ / 60);
  if (g_uart) for (auto& u : *g_uart)
    printf("  with the UART at %6.0f baud: %.1f s = %.2f min (UART alone %.1f s; the UART holds up %.1f%% of pixels; %.2f bits per pixel)\n",
           u.baud, u.frame() * scale, u.frame() * scale / 60, u.bits / u.baud * scale, 100.0 * u.limited / u.pixels, (double)u.bits / u.pixels);
  printf("  checks: clamps %llu total (expected: tests of far objects that miss anyway)\n", (unsigned long long)st.sat);
  printf("          clamps in ray/hit point/out-arrow math %llu (should be near 0; ground hits more than 256 from 0, 0)\n", (unsigned long long)st.satcrit);
  printf("          ground divide clamped -> sky %llu\n", (unsigned long long)st.gclamp);
  printf("          n + random arrow = 0: %llu | M_COS input outside CORDIC range: %llu | accumulator over 17 bits: %llu\n",
         (unsigned long long)st.nearzero, (unsigned long long)st.cordic_out, (unsigned long long)st.acc_over);
#ifdef FLIPCHECK
  printf("          triangle winners where the back-side flag and the old n . D rule disagree: %llu\n", (unsigned long long)st.flipdiff);
#endif
}

int main(int argc, char** argv) {
  if (argc < 2) { fprintf(stderr, "usage: %s scene.txt [-size N] [-spp N] [-fixed|-float] [-lfsr32] [-linear] [-seed N] [-o NAME]\n", argv[0]); return 1; }
  Opt o; string out = "out"; bool do_fix = true, do_flt = true;
  for (int i = 2; i < argc; i++) {
    string a = argv[i];
    if (a == "-size" && i + 1 < argc) o.size = atoi(argv[++i]);
    else if (a == "-spp" && i + 1 < argc) o.spp = atoi(argv[++i]);
    else if (a == "-o" && i + 1 < argc) out = argv[++i];
    else if (a == "-seed" && i + 1 < argc) o.seed = (uint32_t)strtoul(argv[++i], nullptr, 0);
    else if (a == "-fixed") do_flt = false; else if (a == "-float") do_fix = false;
    else if (a == "-lfsr32") o.lfsr32 = true;
    else if (a == "-linear") o.gamma = false; else die("unknown option " + a);
  }
  Scene sc = load_scene(argv[1]);
  int W = o.size ? o.size : sc.size, spp = o.spp ? o.spp : sc.spp;
  if (W < 64 || W > 512 || (W & (W - 1))) die("image size must be a power of 2, 64..512 (9-bit pixel counters)");
  if (spp < 1 || spp > MAXSPP || (spp & (spp - 1))) die("samples per pixel must be 1, 2, 4, 8, 16 or 32");
  vector<uint16_t> mem = pack(sc, spp);
  vector<uint8_t> a, b;
  if (do_fix) {
    st = Stats{}; Chip<Fix> chip(mem, o, W);
    vector<UartSim> uarts = {UartSim(115200), UartSim(230400)};
    g_uart = &uarts;
    a = chip.render(); write_bmp(out + "_fixed.bmp", a, W, o.gamma);
    printf("16-bit chip model:\n"); report(W, spp);
    g_uart = nullptr;
  }
  if (do_flt) {
    st = Stats{}; Chip<Flt> chip(mem, o, W);
    b = chip.render(); write_bmp(out + "_float.bmp", b, W, o.gamma);
    printf("float reference: %.3f segments per sample\n", (double)st.segs / st.samples);
  }
  auto psnr = [](const vector<uint8_t>& x, const vector<uint8_t>& y) {
    double se = 0; for (size_t i = 0; i < x.size(); i++) se += (double)(x[i] - y[i]) * (x[i] - y[i]);
    return 10 * log10(255.0 * 255.0 / max(se / x.size(), 1e-12));
  };
  if (do_fix && do_flt) {
    vector<uint8_t> d(a.size());
    for (size_t i = 0; i < a.size(); i++) d[i] = (uint8_t)min(255, abs(a[i] - b[i]) * 8);
    write_bmp(out + "_diff.bmp", d, W, false);
    Opt o2 = o; o2.seed = o.seed * 7919 + 12345;  // noise floor: same float flow, other random start
    Chip<Flt> chip(mem, o2, W);
    printf("fixed vs float PSNR %.1f dB; noise floor (float vs float, other random start) %.1f dB\n",
           psnr(a, b), psnr(b, chip.render()));
    printf("  (similar numbers = 16-bit math adds no error beyond the %d-sample noise)\n", spp);
  }
  return 0;
}
