# Top-level cocotb testbench for the functional units (FU Control + ALU, multiplier, CORDIC).
#what this tb checks 
#Operands are read from the right registers in the accept cycle
#The result goes to the right RD.
#ALU and multiplier write 1 cycle after accept; CORDIC writes within its worst-case latency.
#resp_done pulses together with the register write.
#ALU and multiplier never stall while CORDIC is busy.
#Nothing hangs, nothing stray gets written, and resets behave.
#Macro-op cycle counts match the decode.md table.

#NOT RUN YET since rtl is unfinished. 

import random
from collections import Counter, deque
from dataclasses import dataclass
 
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly, RisingEdge
 
CLK_PERIOD_NS = 40
ALU_LATENCY = 1
MUL_LATENCY = 1
 
# Encodings 
U_ADD, U_SUB, U_EQ, U_NE, U_LT, U_GE = 0, 1, 2, 3, 4, 5
U_MUL, U_DIV, U_SQRT, U_COS, U_MAG = 6, 7, 8, 9, 11
NAMES = {0: "ADD", 1: "SUB", 2: "EQ", 3: "NE", 4: "LT", 5: "GE", 6: "MUL",
         7: "DIV", 8: "SQRT", 9: "COS", 11: "MAG"}
ALU, MUL, CORDIC = "ALU", "MUL", "CORDIC"
CORDIC_MAX_LATENCY = {U_DIV: 17, U_COS: 18, U_MAG: 19, U_SQRT: 23}  # cordic.md
 
 
def unit_of(op):
    if op <= U_GE:
        return ALU
    if op == U_MUL:
        return MUL
    return CORDIC
 
 
def expected_result(op, a, b, fmt):
    """Expected 16-bit result of a micro-op, or None to skip the value check.
    TODO: hook up the reference model here."""
    return None
 
 
# Micro-op ROM
ROM = {
    "VADD": [(U_ADD, 0, 0, 3, 0), (U_ADD, 1, 1, 4, 0), (U_ADD, 2, 2, 5, 0)],
    "VSUB": [(U_SUB, 0, 0, 3, 0), (U_SUB, 1, 1, 4, 0), (U_SUB, 2, 2, 5, 0)],
    "SCAL_VEC": [(U_MUL, 1, 0, 4, 0), (U_MUL, 2, 0, 5, 0), (U_MUL, 0, 0, 3, 0)],
    "DOT": [(U_MUL, 0, 0, 3, 0), (U_MUL, 1, 1, 4, 0), (U_MUL, 2, 2, 5, 0),
            (U_ADD, 0, 0, 1, 1), (U_ADD, 0, 0, 2, 1)],
    "CROSS": [(U_MUL, 6, 2, 4, 0), (U_MUL, 2, 2, 3, 0), (U_MUL, 4, 0, 4, 0),
              (U_MUL, 3, 1, 3, 0), (U_MUL, 1, 1, 5, 0), (U_MUL, 5, 0, 5, 0),
              (U_SUB, 0, 1, 6, 1), (U_SUB, 1, 2, 5, 0), (U_SUB, 2, 4, 3, 0)],
    "NORM": [(U_MAG, 4, 0, 1, 0), (U_MAG, 4, 4, 2, 1), (U_DIV, 4, 3, 4, 1),
             (U_MUL, 0, 4, 0, 1), (U_MUL, 1, 4, 1, 0), (U_MUL, 2, 4, 2, 0)],
    "SPHERE_NORM": [(U_DIV, 1, 4, 0, 0), (U_DIV, 2, 5, 0, 0), (U_DIV, 0, 3, 0, 0)],
    "VMUL": [(U_MUL, 0, 0, 3, 0), (U_MUL, 1, 1, 4, 0), (U_MUL, 2, 2, 5, 0)],
}
SCALAR = {"ADD": U_ADD, "SUB": U_SUB, "EQ": U_EQ, "NE": U_NE, "LT": U_LT, "GE": U_GE,
          "MUL": U_MUL, "DIV": U_DIV, "SQRT": U_SQRT, "COS": U_COS, "MAG": U_MAG}
# decode.md timing table, accept to reply. CORDIC ones are worst cases.
MACRO_CYCLES = {"ADD": 3, "SUB": 3, "EQ": 3, "NE": 3, "LT": 3, "GE": 3, "MUL": 3,
                "DIV": 19, "COS": 20, "MAG": 21, "SQRT": 25, "VADD": 7, "VSUB": 7,
                "SCAL_VEC": 7, "VMUL": 7, "DOT": 11, "CROSS": 14,
                "SPHERE_NORM": 57, "NORM": 65}
USES_CORDIC = {"DIV", "COS", "MAG", "SQRT", "SPHERE_NORM", "NORM"}
 
 
def h(v):
    return f"16'h{v & 0xFFFF:04X}"
 
 
# Environment
@dataclass
class Item:
    op: int = None # None: register file load only
    rd: int = 0
    rs1: int = 0
    rs2: int = 0
    fmt: int = 0
    direct: bool = False
    u1: int = 0
    v1: int = 0
    barrier: bool = False # wait until nothing is in flight
    load: tuple = None # ((u1, u2, u3), (v1, v2, v3)) loaded this cycle
    idle_before: int = 0
    macro: "Macro" = None
    a: int = None
    b: int = None
    accept_cycle: int = None
 
    @property
    def unit(self):
        return unit_of(self.op)
 
    @property
    def word(self):
        return (self.rd << 10) | (self.rs1 << 7) | (self.rs2 << 4) | self.op
 
    def __str__(self):
        if self.op is None:
            return "load"
        src = f"{h(self.u1)}, {h(self.v1)} (direct)" if self.direct else f"R{self.rs1}, R{self.rs2}"
        s = f"{NAMES.get(self.op, self.op)} R{self.rd} <- {src} fmt={self.fmt}"
        return s + (f" in {self.macro.name}" if self.macro else "")
 
 
@dataclass
class Macro:
    name: str
    remaining: int = 0
    load_cycle: int = None
    last_done: int = None
    complete: bool = False
 
    @property
    def cycles(self):
        done = self.last_done - self.load_cycle + 1
        return done + (1 if self.name in SCALAR else 2)
 
 
class FuEnv:
    def __init__(self, dut):
        self.dut, self.clk, self.log = dut, dut.clk, dut._log
        self.rng = random.Random(random.getrandbits(32))  # follows RANDOM_SEED
        self.queue = deque()
        self.cur = None
        self.accepted = False
        self.in_reset = True
        self.fatal = False
        self.cycle = 0
        self.regs = [0] * 8 # shadow register file
        self.inflight = []
        self.macros = []
        self.errors = []
        self.n_accepted = self.n_written = self.n_dropped = 0
        self.stalls = Counter()
        self.overlap_cycles = 0
        self.last_load_item = None
 
    # setup 
    async def start(self):
        d = self.dut
        cocotb.start_soon(Clock(self.clk, CLK_PERIOD_NS, units="ns").start())
        d.rst_n.value = 0
        d.micro_req_valid.value = 0
        d.rf_load.value = 0
        d.rf_load_u.value = 0
        d.rf_load_v.value = 0
        self._garbage()
        cocotb.start_soon(self._monitor())
        cocotb.start_soon(self._driver())
        await self.reset(5)
 
    async def reset(self, cycles=3):
        self.in_reset = True
        self.queue.clear()
        await RisingEdge(self.clk)
        self.dut.rst_n.value = 0
        await ClockCycles(self.clk, cycles)
        self.dut.rst_n.value = 1
        self.in_reset = False
        await RisingEdge(self.clk)
 
    def error(self, msg):
        self.errors.append(msg)
        self.log.error(f"[FU @cycle {self.cycle}] {msg}")
 
    # stimulus 
    def _push(self, it):
        it._idle_left = it.idle_before
        self.queue.append(it)
        return it
 
    def issue(self, op, rd, rs1, rs2, fmt=0, barrier=False, idle_before=0):
        return self._push(Item(op=op, rd=rd, rs1=rs1, rs2=rs2, fmt=fmt,
                               barrier=bool(barrier), idle_before=idle_before))
 
    def issue_direct(self, op, u1, v1, rd=0, fmt=0, load=None, idle_before=0):
        return self._push(Item(op=op, rd=rd, rs1=0, rs2=3, fmt=fmt, direct=True,
                               u1=u1 & 0xFFFF, v1=v1 & 0xFFFF, load=load,
                               barrier=True, idle_before=idle_before))
 
    def load(self, u, v, idle_before=0):
        return self._push(Item(load=(tuple(x & 0xFFFF for x in u), tuple(x & 0xFFFF for x in v)),
                               barrier=True, idle_before=idle_before))
 
    def macro(self, name, fmt, u, v, idle_before=0):
        """Queue a macro-op the way the Decode Unit runs it."""
        u, v = tuple(x & 0xFFFF for x in u), tuple(x & 0xFFFF for x in v)
        m = Macro(name)
        if name in SCALAR:
            items = [self.issue_direct(SCALAR[name], u[0], v[0], fmt=fmt, load=(u, v),
                                       idle_before=idle_before)]
        else:
            items = [self.load(u, v, idle_before=idle_before)]
            items += [self.issue(op, rd, rs1, rs2, fmt, bar) for op, rd, rs1, rs2, bar in ROM[name]]
        for it in items:
            it.macro = m
        m.remaining = sum(1 for it in items if it.op is not None)
        self.macros.append(m)
        return m
 
    async def drain(self, timeout=2_000_000):
        for _ in range(timeout):
            if self.fatal:
                return
            if not self.queue and self.cur is None and not self.inflight:
                await ClockCycles(self.clk, 5)
                return
            await RisingEdge(self.clk)
        self.error(f"drain timed out after {timeout} cycles")
 
    def finish(self):
        for m in self.macros:
            if not m.complete:
                continue
            want = MACRO_CYCLES[m.name]
            if m.name in USES_CORDIC:
                if m.cycles > want:
                    self.error(f"{m.name} took {m.cycles} cycles, worst case {want}")
            elif m.cycles != want:
                self.error(f"{m.name} took {m.cycles} cycles, decode.md says {want}")
        self.log.info(f"[FU] accepted={self.n_accepted} written={self.n_written} "
                      f"dropped={self.n_dropped} stalls={dict(self.stalls)} "
                      f"overlap_cycles={self.overlap_cycles}")
        if self.errors:
            raise AssertionError(f"{len(self.errors)} error(s). First: {self.errors[0]}")
        assert self.n_accepted == self.n_written + self.n_dropped, "micro-ops never written"
 
    # driver 
    def _garbage(self):
        d, r = self.dut, self.rng
        d.micro_req_op.value = r.getrandbits(13)
        d.micro_req_fmt.value = r.getrandbits(1)
        d.micro_req_direct.value = r.getrandbits(1)
        d.micro_req_u1.value = r.getrandbits(16)
        d.micro_req_v1.value = r.getrandbits(16)
 
    def _idle(self):
        self.dut.micro_req_valid.value = 0
        self._garbage()
 
    async def _driver(self):
        d, waited = self.dut, 0
        while True:
            await RisingEdge(self.clk)
            d.rf_load.value = 0
            if self.in_reset or self.fatal:
                self.cur = None
                self._idle()
                continue
            if self.cur is not None:
                if self.accepted:
                    self.cur = None
                else:
                    waited += 1
                    if waited > 200:
                        self.error(f"micro.req_ready low for 200 cycles: {self.cur}")
                        self.fatal, self.cur = True, None
                        self._idle()
                    continue
            if not self.queue:
                self._idle()
                continue
            nxt = self.queue[0]
            if nxt._idle_left > 0:
                nxt._idle_left -= 1
                self._idle()
                continue
            if nxt.barrier and self.inflight:
                self._idle()
                continue
            it = self.queue.popleft()
            if it.load is not None:
                u, v = it.load
                d.rf_load.value = 1
                d.rf_load_u.value = (u[2] << 32) | (u[1] << 16) | u[0]
                d.rf_load_v.value = (v[2] << 32) | (v[1] << 16) | v[0]
                self.last_load_item = it
            if it.op is None:
                self._idle()
                continue
            d.micro_req_valid.value = 1
            d.micro_req_op.value = it.word
            d.micro_req_fmt.value = it.fmt
            d.micro_req_direct.value = int(it.direct)
            d.micro_req_u1.value = it.u1 if it.direct else self.rng.getrandbits(16)
            d.micro_req_v1.value = it.v1 if it.direct else self.rng.getrandbits(16)
            self.cur, self.accepted, waited = it, False, 0
 
    # monitor 
    def _int(self, sig, name):
        v = sig.value
        if not v.is_resolvable:
            self.error(f"{name} is X/Z ({v.binstr})")
            return 0
        return int(v)
 
    def _max_latency(self, it):
        return {ALU: ALU_LATENCY, MUL: MUL_LATENCY}.get(it.unit) or CORDIC_MAX_LATENCY[it.op]
 
    async def _monitor(self):
        d = self.dut
        while True:
            await FallingEdge(self.clk)
            await ReadOnly()
            self.cycle += 1
 
            if not d.rst_n.value.is_resolvable or int(d.rst_n.value) == 0:
                if d.micro_resp_done.value.is_resolvable and int(d.micro_resp_done.value):
                    self.error("micro.resp_done high in reset")
                if d.rf_wen.value.is_resolvable and int(d.rf_wen.value):
                    self.error("rf_wen high in reset")
                self.n_dropped += len(self.inflight)
                self.inflight.clear()
                self.regs = [0] * 8
                continue
 
            wen = self._int(d.rf_wen, "rf_wen")
            done = self._int(d.micro_resp_done, "micro.resp_done")
            write, cordic_freed = None, False
 
            # 1. register writes
            if wen != done:
                self.error(f"micro.resp_done={done} but rf_wen={wen}: must pulse together")
            if wen:
                waddr = self._int(d.rf_waddr, "rf_waddr")
                wdata = d.rf_wdata.value
                cands = [it for it in self.inflight if it.rd == waddr]
                if not cands:
                    self.error(f"write to R{waddr} with no micro-op in flight for R{waddr}")
                else:
                    it = cands[0]
                    self.inflight.remove(it)
                    self.n_written += 1
                    lat = self.cycle - it.accept_cycle
                    lim = self._max_latency(it)
                    if it.unit == CORDIC:
                        cordic_freed = True
                        if not 1 <= lat <= lim:
                            self.error(f"{it}: CORDIC latency {lat}, worst case {lim}")
                    elif lat != lim:
                        self.error(f"{it}: written {lat} cycles after accept, expected {lim}")
                    if not wdata.is_resolvable:
                        self.error(f"{it}: rf_wdata is X/Z ({wdata.binstr})")
                    else:
                        res = int(wdata)
                        exp = expected_result(it.op, it.a, it.b, it.fmt)
                        if exp is not None and res != exp:
                            self.error(f"{it} [A={h(it.a)} B={h(it.b)}]: wrote {h(res)}, expected {h(exp)}")
                        write = (waddr, res)
                    if it.macro:
                        it.macro.remaining -= 1
                        it.macro.last_done = self.cycle
                        if it.macro.remaining == 0:
                            it.macro.complete = True
 
            # 2. requests
            valid = self._int(d.micro_req_valid, "micro.req_valid")
            ready = self._int(d.micro_req_ready, "micro.req_ready")
            cordic_busy = any(i.unit == CORDIC for i in self.inflight)
            if valid and self.cur is not None:
                it = self.cur
                if ready:
                    if it.direct:
                        it.a, it.b = it.u1, it.v1
                    else:
                        it.a, it.b = self.regs[it.rs1], self.regs[it.rs2]
                        ra1 = self._int(d.rf_raddr1, "rf_raddr1")
                        ra2 = self._int(d.rf_raddr2, "rf_raddr2")
                        if ra1 != it.rs1 or (it.op != U_SQRT and ra2 != it.rs2):
                            self.error(f"{it}: read R{ra1}, R{ra2} in the accept cycle, "
                                       f"expected R{it.rs1}, R{it.rs2}")
                    if it.unit == CORDIC and cordic_busy:
                        self.error(f"{it}: accepted while CORDIC is busy")
                    it.accept_cycle = self.cycle
                    self.inflight.append(it)
                    self.n_accepted += 1
                    self.accepted = True
                else:
                    self.stalls[it.unit] += 1
                    if it.unit != CORDIC:
                        self.error(f"{it}: {it.unit} micro-op stalled; only CORDIC ones may wait")
                    elif not cordic_busy and not cordic_freed:
                        self.error(f"{it}: CORDIC micro-op stalled while CORDIC is idle")
            if len({i.unit for i in self.inflight}) > 1:
                self.overlap_cycles += 1
 
            # 3. register file update at this edge (load has priority)
            if self._int(d.rf_load, "rf_load"):
                u = self._int(d.rf_load_u, "rf_load_u")
                v = self._int(d.rf_load_v, "rf_load_v")
                lit = self.last_load_item
                if lit is not None and lit.macro is not None:
                    lit.macro.load_cycle = self.cycle
                self.regs[0:3] = [(u >> (16 * i)) & 0xFFFF for i in range(3)]
                self.regs[3:6] = [(v >> (16 * i)) & 0xFFFF for i in range(3)]
            elif write:
                self.regs[write[0]] = write[1]
 
            # 4. hang detection
            for it in list(self.inflight):
                if self.cycle - it.accept_cycle > self._max_latency(it) + 50:
                    self.error(f"{it}: never written")
                    self.inflight.remove(it)
                    self.n_written += 1
 
 
# Stimulus helpers
CORNERS = [0x0000, 0x0001, 0xFFFF, 0x7FFF, 0x8000, 0x0080, 0xFF80, 0x4000, 0xC000, 0x1234]
COS_LIMIT = 28557  # |angle| <= 1.743 rad in DIR
 
 
def rand16(rng):
    r = rng.random()
    if r < 0.15:
        return rng.choice(CORNERS)
    if r < 0.3:
        return rng.randint(-256, 255) & 0xFFFF
    return rng.getrandbits(16)
 
 
def sgn(v):
    return v - 0x10000 if v & 0x8000 else v
 
 
def macro_operands(rng, name):
    """(fmt, u, v) the RTU could legally send for this macro-op."""
    fmt = rng.getrandbits(1)
    u = [rand16(rng) for _ in range(3)]
    v = [rand16(rng) for _ in range(3)]
    if name == "DIV":
        while v[0] == 0:
            v[0] = rand16(rng)
    elif name == "SQRT":
        u[0] &= 0x7FFF
    elif name == "COS":
        v[0] = rng.randint(-COS_LIMIT, COS_LIMIT) & 0xFFFF
    elif name == "NORM":
        fmt = 1
        while True:
            u = [rng.randint(-16384, 16384) for _ in range(3)]
            if max(abs(x) for x in u) >= 8192:
                break
        u = [x & 0xFFFF for x in u]
        v[0] = 0x4000
    elif name == "SPHERE_NORM":
        r = rng.randint(1, 32767)
        u[0] = r
        v = [rng.randint(-r, r) & 0xFFFF for _ in range(3)]
    return fmt, u, v
 
 
async def run(env):
    await env.drain()
    env.finish()
 
 
# Tests
@cocotb.test()
async def test_reset_idle(dut):
    """After reset: ready, no writes, no resp_done."""
    env = FuEnv(dut)
    await env.start()
    for _ in range(10):
        await ReadOnly()
        assert int(dut.micro_req_ready.value) == 1, "idle FU Control must be ready"
        assert int(dut.rf_wen.value) == 0 and int(dut.micro_resp_done.value) == 0
        await RisingEdge(dut.clk)
    await run(env)
 
 
@cocotb.test()
async def test_direct_ops(dut):
    """Micro-ops with operands on the request (req_direct): all 11 scalar
    macro-ops on corner values with the load in the same cycle, then every
    opcode written to every other RD."""
    env = FuEnv(dut)
    await env.start()
    for name in SCALAR:
        for a in CORNERS:
            for b in CORNERS:
                fmt, u, v = macro_operands(env.rng, name)
                u[0], v[0] = a, b
                if (name == "DIV" and b == 0) or (name == "COS" and abs(sgn(b)) > COS_LIMIT):
                    continue
                if name == "SQRT":
                    u[0] &= 0x7FFF
                env.macro(name, fmt, u, v)
    for op in NAMES:
        for rd in range(1, 8):
            a, b = rand16(env.rng), rand16(env.rng)
            if op == U_DIV and b == 0:
                b = 0x0100
            if op == U_COS:
                b = env.rng.randint(-COS_LIMIT, COS_LIMIT)
            if op == U_SQRT:
                a &= 0x7FFF
            env.issue_direct(op, a, b, rd=rd, fmt=env.rng.getrandbits(1))
    await run(env)
 
 
@cocotb.test()
async def test_random_macro_stream(dut):
    """600 random macro-ops back to back, like the RTU would send them."""
    env = FuEnv(dut)
    await env.start()
    names = list(SCALAR) + list(ROM)
    for _ in range(600):
        name = env.rng.choice(names)
        env.macro(name, *macro_operands(env.rng, name), idle_before=env.rng.choice([1, 2, 3]))
    await run(env)
 
 
@cocotb.test()
async def test_alu_mul_back_to_back(dut):
    """5000 random ALU/MUL micro-ops, one per cycle, no barriers."""
    env = FuEnv(dut)
    await env.start()
    env.load([rand16(env.rng) for _ in range(3)], [rand16(env.rng) for _ in range(3)])
    for _ in range(5000):
        op = env.rng.choice([U_ADD, U_SUB, U_EQ, U_NE, U_LT, U_GE, U_MUL, U_MUL])
        env.issue(op, env.rng.randrange(8), env.rng.randrange(8), env.rng.randrange(8),
                  fmt=env.rng.getrandbits(1))
    await run(env)
    assert env.stalls[ALU] == 0 and env.stalls[MUL] == 0
 
 
@cocotb.test()
async def test_alu_mul_while_cordic_busy(dut):
    """ALU/MUL micro-ops must run while CORDIC is busy; a second CORDIC op
    must wait. Overlap stays in the first 12 cycles so no two units finish
    in the same cycle."""
    env = FuEnv(dut)
    await env.start()
    for _ in range(60):
        env.load([rand16(env.rng) for _ in range(3)], [rand16(env.rng) for _ in range(3)])
        env.issue(env.rng.choice([U_DIV, U_SQRT, U_COS, U_MAG]), 6, 0, 1, fmt=env.rng.getrandbits(1))
        for _ in range(env.rng.randint(1, 10)):
            env.issue(env.rng.choice([U_ADD, U_SUB, U_MUL, U_GE]), env.rng.randrange(6),
                      env.rng.randrange(6), env.rng.randrange(6), fmt=env.rng.getrandbits(1))
        env.issue(U_MAG, 7, 0, 1)
    await run(env)
    assert env.overlap_cycles > 0, "never had two units busy at once"
    assert env.stalls[CORDIC] > 0, "a CORDIC micro-op never had to wait"
 
 
@cocotb.test()
async def test_reset_mid_macro(dut):
    """Reset during NORM, CROSS and SPHERE_NORM, then more macro-ops."""
    env = FuEnv(dut)
    await env.start()
    for name, delay in (("NORM", 10), ("NORM", 30), ("CROSS", 4), ("SPHERE_NORM", 45)):
        env.macro(name, *macro_operands(env.rng, name))
        await ClockCycles(dut.clk, delay)
        await env.reset(2)
        for after in ("VADD", "MAG", "DOT"):
            env.macro(after, *macro_operands(env.rng, after), idle_before=1)
        await env.drain()
    env.finish()