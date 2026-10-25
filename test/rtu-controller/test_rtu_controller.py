#Cocotb tests for the RTU controller (the FSM inside src/rtu/rtu.sv)
#To run: make (in this folder)
#The top module is our test wrapper tb_rtu_controller.sv
#This file acts as the SRAM, and sets done/hit_kind/material on the fake sub-blocks
#Spec we check against: docs/modules/rtu/rtu.md and docs/encoding/scene.md

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, ReadOnly, RisingEdge

CLK_PERIOD_NS = 40  #25 MHz

#values of active (rtu_blk_t in tinytracer_pkg.sv)
BLK_CTRL, BLK_RAY_GEN, BLK_ISECT, BLK_SHADER = 0, 1, 2, 3

HDR_WORDS = 17

#Header words 0 to 16 (see docs/encoding/scene.md)
#Every word is different so we can tell if one ends up in the wrong register
HEADER = [
    0x2C4A, 0x2C4B, 0xF2B0,  #w0-w2: F.x, F.y, F.z
    0x2D41, 0xD2BF, 0x0000,  #w3-w5: R.x, R.y, R.z
    0x0969, 0x096A, 0x3E97,  #w6-w8: U.x, U.y, U.z
    0xEBF0, 0xFF6E, 0x8CFF,  #w9-w11: sky colours
    0x1122, 0x3344, 0x5566,  #w12-w14: ground colours
    (4 << 3) | 3,            #w15: BV_NUM = 4, SPP_LOG2 = 3
    0x0800,                  #w16: CAM_Z = 16.0
]


def vec3(x, y, z):
    #vec3_t is packed as {z, y, x}, so x is the lowest 16 bits
    return (z << 32) | (y << 16) | x


async def sram_responder(dut, reads):
    #Fake SRAM (timing from docs/modules/sram/sram_control.md)
    #If we take an address in cycle k, the data comes back in cycle k + 2
    #We take the next address in the same cycle the data comes back, so 2 cycles per word
    #Every address we take gets added to reads
    pending = None #address we are waiting on
    wait = 0 #cycles left until its data comes back
    while True:
        resp = pending is not None and wait == 0
        ready = pending is None or resp
        dut.sram_resp_valid.value = int(resp)
        dut.sram_resp_rdata.value = HEADER[pending] if resp and pending < HDR_WORDS else 0
        dut.sram_req_ready.value = int(ready)

        await ReadOnly()
        accepted = ready and int(dut.sram_req_valid.value) == 1
        addr = int(dut.sram_req_raddr.value)

        await RisingEdge(dut.clk)
        if resp:
            pending = None
        elif pending is not None:
            wait -= 1
        if accepted:
            reads.append(addr)
            pending, wait = addr, 1


async def setup(dut):
    #Start the clock and the fake SRAM, hold reset for a bit, then let go
    #Returns the list of addresses the SRAM gets asked for
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, "ns").start())

    dut.rst_n.value = 0
    dut.render.value = 0
    dut.img_w.value = 512
    dut.img_h.value = 512
    dut.u_rtu.u_ray_generator.done.value = 0
    dut.u_rtu.u_intersection_unit.done.value = 0
    dut.u_rtu.u_intersection_unit.hit_kind.value = 0
    dut.u_rtu.u_intersection_unit.material.value = 0
    dut.u_rtu.u_shader_core.done.value = 0

    reads = []
    cocotb.start_soon(sram_responder(dut, reads))

    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    return reads


async def send_render(dut):
    #Pulse render high for one cycle
    dut.render.value = 1
    await RisingEdge(dut.clk)
    dut.render.value = 0


def starts(dut):
    #start signals of the ray generator, intersection unit and shader core
    rtu = dut.u_rtu
    return int(rtu.rg_start.value), int(rtu.iu_start.value), int(rtu.sh_start.value)


async def wait_for_start(dut, name, max_cycles):
    #Wait for rg_start, iu_start or sh_start to go high and return the mode
    #Fails if it takes too long or if a different block starts first
    rtu = dut.u_rtu
    for _ in range(max_cycles):
        await ReadOnly()
        if int(getattr(rtu, f"{name}_start").value):
            return int(getattr(rtu, f"{name}_mode").value)
        assert starts(dut) == (0, 0, 0), f"unexpected start {starts(dut)} while waiting for {name}_start"
        await RisingEdge(dut.clk)
    assert False, f"{name}_start not seen within {max_cycles} cycles"


async def check_one_cycle_pulse(dut, name):
    #Call this in the cycle start is high, it should be low again next cycle
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(getattr(dut.u_rtu, f"{name}_start").value) == 0, f"{name}_start held for more than one cycle"


async def wait_for_header(dut, reads, max_cycles=2 * HDR_WORDS + 20):
    #Wait until all 17 header words have been read
    for _ in range(max_cycles):
        if len(reads) >= HDR_WORDS:
            return
        await RisingEdge(dut.clk)
    assert False, f"only {len(reads)} of {HDR_WORDS} header reads after {max_cycles} cycles: {reads}"


async def render_to_raygen_start(dut, reads):
    #Steps a few tests share: send render, load the header, see the first ray generator start
    await send_render(dut)
    mode = await wait_for_start(dut, "rg", 2 * HDR_WORDS + 20)
    assert len(reads) == HDR_WORDS, f"rg_start before the header load finished: reads = {reads}"
    assert mode == 0, f"expected rg_mode 0 (camera ray), got {mode}"
    await check_one_cycle_pulse(dut, "rg")


@cocotb.test()
async def test_reset_idle(dut):
    #After reset with no render, the controller should just sit there
    #No starts and no SRAM reads
    reads = await setup(dut)

    for i in range(20):
        await ReadOnly()
        assert starts(dut) == (0, 0, 0), f"start pulse {starts(dut)} while idle (cycle {i})"
        assert int(dut.sram_req_valid.value) == 0, f"SRAM read request while idle (cycle {i})"
        await RisingEdge(dut.clk)
    assert reads == [], f"SRAM reads while idle: {reads}"


@cocotb.test()
async def test_start_render(dut):
    #Render while idle should start loading the header
    #The first read should be address 0, with active = BLK_CTRL
    reads = await setup(dut)
    await ClockCycles(dut.clk, 5)
    await send_render(dut)

    for _ in range(5):
        await ReadOnly()
        if int(dut.sram_req_valid.value):
            break
        await RisingEdge(dut.clk)
    else:
        assert False, "no SRAM read within 5 cycles of render"

    assert int(dut.sram_req_raddr.value) == 0, f"first header read at {int(dut.sram_req_raddr.value)}, expected 0"
    assert int(dut.u_rtu.active.value) == BLK_CTRL, f"active = {int(dut.u_rtu.active.value)} during header load, expected BLK_CTRL"
    assert starts(dut) == (0, 0, 0), "sub-block started during header load"


@cocotb.test()
async def test_header_load(dut):
    #Should read exactly 17 words, addresses 0 to 16 in order
    #Then check a few of the header registers got the right values
    reads = await setup(dut)
    await send_render(dut)
    await wait_for_header(dut, reads)
    await ClockCycles(dut.clk, 20)  #make sure there is no 18th read

    assert reads == list(range(HDR_WORDS)), f"header reads {reads}, expected 0..16 in order"

    rtu = dut.u_rtu
    assert int(rtu.hdr_f.value) == vec3(*HEADER[0:3]), f"hdr_f = {int(rtu.hdr_f.value):#x}"
    assert int(rtu.cam_z.value) == HEADER[16], f"cam_z = {int(rtu.cam_z.value):#x}"
    assert int(dut.spp_log2.value) == HEADER[15] & 0x7, f"spp_log2 = {int(dut.spp_log2.value)}"


@cocotb.test()
async def test_header_done_starts_raygen(dut):
    #After the header is loaded, the controller should start the ray generator
    #in mode 0 (camera ray) for one cycle, and set active to the ray generator
    reads = await setup(dut)
    await render_to_raygen_start(dut, reads)
    #active changes at the end of the start cycle, so it should be BLK_RAY_GEN now
    assert int(dut.u_rtu.active.value) == BLK_RAY_GEN, f"active = {int(dut.u_rtu.active.value)}, expected BLK_RAY_GEN"


@cocotb.test()
async def test_raygen_done_starts_isect(dut):
    #When the ray generator is done, the controller should start the intersection unit in mode 0 (search)
    #The spec lets iu_start happen in the same cycle as rg_done, but for now we allow up to 2 cycles
    #TODO: make this same cycle only once the FSM is done
    reads = await setup(dut)
    await render_to_raygen_start(dut, reads)

    #Pretend the ray generator is busy for a few cycles, nothing else should start
    for _ in range(5):
        await ReadOnly()
        assert starts(dut) == (0, 0, 0), f"start {starts(dut)} before rg_done"
        await RisingEdge(dut.clk)

    rg_done = dut.u_rtu.u_ray_generator.done
    rg_done.value = 1
    for delay in range(3):
        await ReadOnly()
        if int(dut.u_rtu.iu_start.value):
            break
        await RisingEdge(dut.clk)
        rg_done.value = 0  #done is only high for one cycle
    else:
        assert False, "iu_start not seen within 2 cycles of rg_done"

    mode = int(dut.u_rtu.iu_mode.value)
    assert mode == 0, f"expected iu_mode 0 (search), got {mode}"
    assert int(dut.u_rtu.rg_start.value) == 0 and int(dut.u_rtu.sh_start.value) == 0, "other block started with iu_start"
    dut._log.info(f"iu_start {delay} cycle(s) after rg_done")

    await RisingEdge(dut.clk)
    rg_done.value = 0
    await ReadOnly()
    assert int(dut.u_rtu.iu_start.value) == 0, "iu_start held for more than one cycle"