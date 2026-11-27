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

#values of hit_kind and material (hit_kind_t and mat_type_t in tinytracer_pkg.sv)
HIT_SKY, HIT_GROUND, HIT_OBJECT = 0, 1, 2
MAT_DIFFUSE, MAT_EMISSIVE = 0, 3

MAX_BOUNCES = 8

#name of each fake sub-block inside the rtu
BLOCKS = {"rg": "u_ray_generator", "iu": "u_intersection_unit", "sh": "u_shader_core"}

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

#Same header but 1 sample per pixel (SPP_LOG2 = 0), so a whole row of pixels is quick to run
HEADER_1SPP = HEADER[:15] + [(4 << 3) | 0] + HEADER[16:]

IMG_W = 512  #setup drives img_w = 512, and 512 is also the largest image, so a row is 512 pixels


def vec3(x, y, z):
    #vec3_t is packed as {z, y, x}, so x is the lowest 16 bits
    return (z << 32) | (y << 16) | x


async def sram_responder(dut, reads, header):
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
        dut.sram_resp_rdata.value = header[pending] if resp and pending < HDR_WORDS else 0
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


async def setup(dut, header=HEADER):
    #Start the clock and the fake SRAM, hold reset for a bit, then let go
    #The SRAM sends back header for the header reads (HEADER unless a test picks another one)
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
    dut.sram_req_ready.value = 0
    dut.sram_resp_valid.value = 0
    dut.sram_resp_rdata.value = 0

    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1

    #Start the SRAM after reset so it doesn't count a read left over from the last test
    reads = []
    cocotb.start_soon(sram_responder(dut, reads, header))
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
    #No other block should start in that cycle either, since this one just started
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(getattr(dut.u_rtu, f"{name}_start").value) == 0, f"{name}_start held for more than one cycle"
    assert starts(dut) == (0, 0, 0), f"another block started right after {name}_start: {starts(dut)}"
    await RisingEdge(dut.clk)  #leave ReadOnly so the caller can write signals or await ReadOnly again


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


async def done_then_start(dut, done_block, next_block, expected_mode, hit_kind=None, material=None):
    #Pulse done on one block for one cycle, then check the next block starts in the right mode
    #Blocks are "rg", "iu" or "sh". For now the start can be up to 2 cycles after done
    #hit_kind and material are only valid while done is high, so after that we change them
    #to a different legal value. A controller that reads them late will then fail
    #TODO: make this same cycle only once the FSM is done
    rtu = dut.u_rtu
    iu = rtu.u_intersection_unit
    done = getattr(rtu, BLOCKS[done_block]).done
    next_start = getattr(rtu, f"{next_block}_start")
    other_starts = [getattr(rtu, f"{name}_start") for name in BLOCKS if name != next_block]

    def end_done():
        done.value = 0
        if hit_kind is not None:
            iu.hit_kind.value = (hit_kind + 1) % 3  #SKY -> GROUND -> OBJECT -> SKY
        if material is not None:
            iu.material.value = material ^ 3  #DIFFUSE <-> EMISSIVE

    done.value = 1
    if hit_kind is not None:
        iu.hit_kind.value = hit_kind
    if material is not None:
        iu.material.value = material

    for _ in range(3):
        await ReadOnly()
        if int(next_start.value):
            break
        assert starts(dut) == (0, 0, 0), f"wrong block started {starts(dut)} after {done_block} done"
        await RisingEdge(dut.clk)
        end_done()
    else:
        assert False, f"{next_block}_start not seen within 2 cycles of {done_block} done"

    mode = int(getattr(rtu, f"{next_block}_mode").value)
    assert mode == expected_mode, f"expected {next_block}_mode {expected_mode}, got {mode}"
    assert all(int(s.value) == 0 for s in other_starts), f"another block started with {next_block}_start: {starts(dut)}"

    await RisingEdge(dut.clk)
    end_done()
    await ReadOnly()
    assert int(next_start.value) == 0, f"{next_block}_start held for more than one cycle"
    assert starts(dut) == (0, 0, 0), f"another block started right after {next_block}_start: {starts(dut)}"
    await RisingEdge(dut.clk)


async def reach_iu_search(dut, header=HEADER):
    #Steps most path tests share: reset, render, header load, ray generator mode 0, then intersection unit mode 0
    reads = await setup(dut, header)
    await render_to_raygen_start(dut, reads)
    await done_then_start(dut, "rg", "iu", 0)


async def diffuse_bounce(dut):
    #One full bounce off a diffuse object, starting from intersection unit mode 0
    #object hit -> read object -> hit point and normal -> attenuation -> bounce ray -> search again
    await done_then_start(dut, "iu", "iu", 1, hit_kind=HIT_OBJECT)
    await done_then_start(dut, "iu", "iu", 2, material=MAT_DIFFUSE)
    await done_then_start(dut, "iu", "sh", 2)
    await done_then_start(dut, "sh", "rg", 1)
    await done_then_start(dut, "rg", "iu", 0)


async def read_pixel(dut):
    #Read pix_x and pix_y, then move on to the next cycle
    await ReadOnly()
    pixel = (int(dut.u_rtu.pix_x.value), int(dut.u_rtu.pix_y.value))
    await RisingEdge(dut.clk)
    return pixel


async def sky_sample(dut):
    #Finish the current sample through the sky path, starting from intersection unit mode 0
    #sky hit -> sky sample -> sample done -> ray generator mode 0 for the next sample -> search again
    #Returns the pixel of the next sample. We read it while the ray generator is busy,
    #since the counter might only change at the end of the start cycle
    await done_then_start(dut, "iu", "sh", 0, hit_kind=HIT_SKY)
    await done_then_start(dut, "sh", "rg", 0)
    pixel = await read_pixel(dut)
    await done_then_start(dut, "rg", "iu", 0)
    return pixel


async def hold_without_done(dut, cycles, expected_active):
    #Keep every done low for some cycles while a block is working
    #The controller should not start anything and active should stay on the working block
    for i in range(cycles):
        await ReadOnly()
        assert starts(dut) == (0, 0, 0), f"start {starts(dut)} while waiting for done (cycle {i})"
        active = int(dut.u_rtu.active.value)
        assert active == expected_active, f"active = {active} while waiting for done, expected {expected_active}"
        await RisingEdge(dut.clk)


async def pulse_ignored_done(dut, block, cycles=5):
    #Pulse done on a block that is NOT active right now. The controller should ignore it,
    #so nothing should start in that cycle or the next few cycles
    done = getattr(dut.u_rtu, BLOCKS[block]).done
    done.value = 1
    for i in range(cycles):
        await ReadOnly()
        assert starts(dut) == (0, 0, 0), f"start {starts(dut)} after {block} done while {block} was not active (cycle {i})"
        await RisingEdge(dut.clk)
        done.value = 0


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


@cocotb.test()
async def test_sky_path(dut):
    #Ray hit nothing, so the shader core should make the sky sample (mode 0)
    await reach_iu_search(dut)
    await done_then_start(dut, "iu", "sh", 0, hit_kind=HIT_SKY)


@cocotb.test()
async def test_object_path(dut):
    #Ray hit an object, so the intersection unit should read the object next (mode 1)
    await reach_iu_search(dut)
    await done_then_start(dut, "iu", "iu", 1, hit_kind=HIT_OBJECT)


@cocotb.test()
async def test_emissive_object(dut):
    #Object glows, so the shader core should make the glow sample (mode 1)
    await reach_iu_search(dut)
    await done_then_start(dut, "iu", "iu", 1, hit_kind=HIT_OBJECT)
    await done_then_start(dut, "iu", "sh", 1, material=MAT_EMISSIVE)


@cocotb.test()
async def test_diffuse_object(dut):
    #Object doesn't glow and we are under the bounce limit
    #so the intersection unit should get the hit point and normal next (mode 2)
    await reach_iu_search(dut)
    await done_then_start(dut, "iu", "iu", 1, hit_kind=HIT_OBJECT)
    await done_then_start(dut, "iu", "iu", 2, material=MAT_DIFFUSE)


@cocotb.test()
async def test_diffuse_bounce(dut):
    #After the hit point and normal, the shader core updates the attenuation (mode 2)
    #Then the ray generator makes the bounce ray, mode = material + 1 = 1 for diffuse
    #material has changed by now, so this also checks the controller saved it
    await reach_iu_search(dut)
    await done_then_start(dut, "iu", "iu", 1, hit_kind=HIT_OBJECT)
    await done_then_start(dut, "iu", "iu", 2, material=MAT_DIFFUSE)
    await done_then_start(dut, "iu", "sh", 2)
    await done_then_start(dut, "sh", "rg", 1)


@cocotb.test()
async def test_ground_bounce(dut):
    #Ray hit the ground. Ground has no object to read, so the controller should skip
    #intersection unit mode 1 and go straight to mode 2 (hit point and normal)
    #Then attenuation (shader mode 2), then a matte bounce (ray generator mode 1)
    #The spec says the intersection unit sets the material to matte for the ground,
    #so we also give diffuse on material while done is high
    await reach_iu_search(dut)
    await done_then_start(dut, "iu", "iu", 2, hit_kind=HIT_GROUND, material=MAT_DIFFUSE)
    await done_then_start(dut, "iu", "sh", 2)
    await done_then_start(dut, "sh", "rg", 1)


@cocotb.test()
async def test_bounce_limit(dut):
    #After 8 bounces the next diffuse hit should not bounce again
    #The shader core should make a black sample instead (mode 3)
    #Doing all 8 bounces first also checks the controller doesn't stop early
    await reach_iu_search(dut)
    for _ in range(MAX_BOUNCES):
        await diffuse_bounce(dut)
    await done_then_start(dut, "iu", "iu", 1, hit_kind=HIT_OBJECT)
    await done_then_start(dut, "iu", "sh", 3, material=MAT_DIFFUSE)


@cocotb.test()
async def test_emissive_at_bounce_limit(dut):
    #A glowing object still gives a glow sample (shader mode 1) at the bounce limit
    #The controller checks the material before the bounce count (step 4 in rtu.md)
    await reach_iu_search(dut)
    for _ in range(MAX_BOUNCES):
        await diffuse_bounce(dut)
    await done_then_start(dut, "iu", "iu", 1, hit_kind=HIT_OBJECT)
    await done_then_start(dut, "iu", "sh", 1, material=MAT_EMISSIVE)


@cocotb.test()
async def test_next_sample_same_pixel(dut):
    #HEADER asks for 8 samples per pixel, so after the first sample the controller
    #should start another camera ray (ray generator mode 0) for the same pixel
    #We assume the first pixel is (0, 0). The docs only say pixels go row by row
    await reach_iu_search(dut)
    first = await read_pixel(dut)
    assert first == (0, 0), f"first pixel is {first}, expected (0, 0)"
    pixel = await sky_sample(dut)
    assert pixel == first, f"pixel changed to {pixel} after 1 of 8 samples"


@cocotb.test()
async def test_last_sample_next_pixel(dut):
    #Each pixel should last exactly 8 samples, then the next pixel starts
    #We go through 2 full pixels, so a sample counter that doesn't reset fails on the second one
    samples = 1 << (HEADER[15] & 0x7)
    await reach_iu_search(dut)
    pixels = [await read_pixel(dut)]
    for _ in range(2 * samples):
        pixels.append(await sky_sample(dut))
    expected = [(n // samples, 0) for n in range(2 * samples + 1)]
    assert pixels == expected, f"pixel of each sample was {pixels}, expected {expected}"


@cocotb.test()
async def test_end_of_row(dut):
    #1 sample per pixel. x should count 0 to 511 with y = 0, then the next pixel is (0, 1)
    #We assume x counts first, since the docs say row by row
    await reach_iu_search(dut, HEADER_1SPP)
    pixel = await read_pixel(dut)
    for n in range(IMG_W + 1):
        expected = (n % IMG_W, n // IMG_W)
        assert pixel == expected, f"sample {n} was at pixel {pixel}, expected {expected}"
        if n < IMG_W:
            pixel = await sky_sample(dut)


@cocotb.test()
async def test_wait_for_done(dut):
    #While a block is working, the controller should just wait for its done
    #We hold the ray generator, then the intersection unit, then the shader core for 30 cycles each
    #and check nothing starts early. After each done the next block should start like normal
    reads = await setup(dut)
    await render_to_raygen_start(dut, reads)
    await hold_without_done(dut, 30, BLK_RAY_GEN)
    await done_then_start(dut, "rg", "iu", 0)
    await hold_without_done(dut, 30, BLK_ISECT)
    await done_then_start(dut, "iu", "sh", 0, hit_kind=HIT_SKY)
    await hold_without_done(dut, 30, BLK_SHADER)
    await done_then_start(dut, "sh", "rg", 0)


@cocotb.test()
async def test_ignores_done_from_idle_block(dut):
    #Only the active block's done should move the controller forward
    #A done from a block that isn't running should do nothing
    reads = await setup(dut)
    await render_to_raygen_start(dut, reads)

    #ray generator is active, so done from the other two should be ignored
    dut.u_rtu.u_intersection_unit.hit_kind.value = HIT_OBJECT
    await pulse_ignored_done(dut, "iu")
    await pulse_ignored_done(dut, "sh")
    await done_then_start(dut, "rg", "iu", 0)

    #intersection unit is active now, so done from the other two should be ignored
    await pulse_ignored_done(dut, "rg")
    await pulse_ignored_done(dut, "sh")
    await done_then_start(dut, "iu", "sh", 0, hit_kind=HIT_SKY)


@cocotb.test()
async def test_reset_mid_render(dut):
    #Reset in the middle of a render should drop everything
    #After reset the controller should sit idle, and a new render should start over:
    #load the header again from address 0 and begin at pixel (0, 0)
    #We use 1 sample per pixel and get to pixel (3, 0) first, so the pixel counter isn't already 0
    reads = await setup(dut, HEADER_1SPP)
    await render_to_raygen_start(dut, reads)
    await done_then_start(dut, "rg", "iu", 0)
    for _ in range(3):
        pixel = await sky_sample(dut)
    assert pixel == (3, 0), f"before reset we are at pixel {pixel}, expected (3, 0)"

    #reset in the middle of the intersection unit search
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    reads.clear()

    for i in range(20):
        await ReadOnly()
        assert starts(dut) == (0, 0, 0), f"start {starts(dut)} after reset with no render (cycle {i})"
        assert int(dut.sram_req_valid.value) == 0, f"SRAM read after reset with no render (cycle {i})"
        await RisingEdge(dut.clk)
    assert reads == [], f"SRAM reads after reset with no render: {reads}"

    await render_to_raygen_start(dut, reads)
    assert reads == list(range(HDR_WORDS)), f"header reads after reset {reads}, expected 0..16 in order"
    pixel = await read_pixel(dut)
    assert pixel == (0, 0), f"first pixel after reset is {pixel}, expected (0, 0)"
