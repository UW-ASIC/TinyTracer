import cocotb
import math
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge
from reference_models.raygen import DIR_FRAC, POS_FRAC, pack_vec3

CLK_NS = 40
MAX_CYCLES = 200

async def tick(dut):
    await RisingEdge(dut.clk)
    await Timer(1, unit = "ns")

async def setup(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_NS, units="ns").start())

    dut.rst_n.value = 0
    dut.start.value = 0
    dut.mode.value = 0
    dut.flip.value = 0

    dut.ray_o.value = pack_vec3(0, 0, 0, POS_FRAC)
    dut.ray_d.value = pack_vec3(0, 0, -1, DIR_FRAC)
    dut.ray_n.value = pack_vec3(0, 0, 1, DIR_FRAC)
    dut.flip.value = 0
    dut.scratch.value = 0
    dut.hdr_f.value = pack_vec3(0, 0, -1, DIR_FRAC)
    dut.hdr_r.value = pack_vec3(1, 0, 0, DIR_FRAC)
    dut.hdr_u.value = pack_vec3(0, 1, 0, DIR_FRAC)
    dut.cam_z.value = 0
    dut.pix_x.value = 0
    dut.pix_y.value = 0
    dut.img_w.value = 64

    dut.req_ready.value = 0
    dut.resp_valid.value = 0
    dut.resp_flag.value = 0
    dut.resp_result.value = 0

    for i in range(5):
        await tick(dut)

    dut.rst_n.value = 1
    await tick(dut)

@cocotb.test()
async def test_idle(dut):
    await setup(dut)

    for _ in range(10):
        assert int(dut.done.value) == 0
        assert int(dut.req_valid.value) == 0
        assert int(dut.o_we.value) == 0
        assert int(dut.d_we.value) == 0
        assert int(dut.scratch_we.value) == 0

        await tick(dut)

# Check that a request remains unchanged until the RTU accepts it.
async def check_request_stall(dut):
    original = (int(dut.req_op.value), int(dut.req_u.value), int(dut.req_v.value), int(dut.req_fmt.value), int(dut.req_we.value), int(dut.req_resize.value))

    for _ in range(3):
        await tick(dut)
        current = (int(dut.req_op.value), int(dut.req_u.value), int(dut.req_v.value), int(dut.req_fmt.value), int(dut.req_we.value), int(dut.req_resize.value))
        assert int(dut.req_valid.value) == 1, "Request dropped while req_ready was low"
        assert current == original, "Request changed while req_ready was low"
        assert int(dut.done.value) == 0, "Finished while request was stalled"
        assert int(dut.o_we.value) == 0 and int(dut.d_we.value) == 0 and int(dut.scratch_we.value) == 0, "Unexpected register write while request was stalled"

# Check that the Ray Generator waits for the RTU response.
async def check_response_wait(dut):
    for _ in range(3):
        await tick(dut)
        assert int(dut.req_valid.value) == 0, "Issued another request before receiving a response"
        assert int(dut.done.value) == 0, "Finished before receiving a response"
        assert int(dut.o_we.value) == 0 and int(dut.d_we.value) == 0 and int(dut.scratch_we.value) == 0, "Unexpected register write before response"

# Mirror - Secondary
async def run_mirror_case(dut, direction, normal, origin, test_handshake=False):
    await setup(dut)

    dut.ray_o.value = pack_vec3(*origin, POS_FRAC)
    dut.ray_d.value = pack_vec3(*direction, DIR_FRAC)
    dut.ray_n.value = pack_vec3(*normal, DIR_FRAC)
    dut.mode.value = 2

    dot_result = sum(d * n for d, n in zip(direction, normal))
    doubled_dot = 2 * dot_result
    scaled_normal = tuple(doubled_dot * n for n in normal)
    reflected = tuple(d - s for d, s in zip(direction, scaled_normal))
    offset = tuple(0.03125 * n for n in normal)
    new_origin = tuple(o + change for o, change in zip(origin, offset))
    expected_direction = pack_vec3(*reflected, DIR_FRAC)
    expected_origin = pack_vec3(*new_origin, POS_FRAC)

    dut.req_ready.value = 0

    dut.start.value = 1
    await tick(dut)
    dut.start.value = 0

    # Dot product.
    received_request = False

    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)

    assert received_request, "Mirror mode never issued a request"
    assert int(dut.req_op.value) == 15, "Expected M_DOT"
    assert int(dut.done.value) == 0, "Ray gen finished before receiving an answer"

    expected_d = pack_vec3(*direction, DIR_FRAC)
    expected_n = pack_vec3(*normal, DIR_FRAC)
    actual_u = int(dut.req_u.value)
    actual_v = int(dut.req_v.value)

    assert ((actual_u == expected_d and actual_v == expected_n) or (actual_u == expected_n and actual_v == expected_d)), "Dot product requested with incorrect direction or normal"
    assert int(dut.req_fmt.value) == 1, "Expected DIR multiplication format for dot product"

    if test_handshake:
        await check_request_stall(dut)

    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0

    if test_handshake:
        await check_response_wait(dut)

    dut.resp_result.value = pack_vec3(dot_result, 0, 0, DIR_FRAC)
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 1, "Dot product was not written to scratch[0]"
    assert int(dut.scratch_wdata.value) == (pack_vec3(dot_result, 0, 0, DIR_FRAC) & 0xFFFF), "Incorrect dot product written to scratch"
    await tick(dut)
    dut.scratch.value = pack_vec3(dot_result, 0, 0, DIR_FRAC) & 0xFFFF
    dut.resp_valid.value = 0
    await Timer(1, unit="ns")

    # Multiply by 2.
    received_request = False

    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)

    assert received_request, "No request after dot product"
    assert int(dut.req_op.value) == 0, "Expected M_ADD"
    assert int(dut.done.value) == 0, "Finished before addition answer"

    expected_scalar = pack_vec3(dot_result, 0, 0, DIR_FRAC) & 0xFFFF
    actual_u = int(dut.req_u.value) & 0xFFFF
    actual_v = int(dut.req_v.value) & 0xFFFF

    assert actual_u == expected_scalar, "Addition has incorrect first operand"
    assert actual_v == expected_scalar, "Addition has incorrect second operand"

    if test_handshake:
        await check_request_stall(dut)

    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0

    if test_handshake:
        await check_response_wait(dut)

    dut.resp_result.value = pack_vec3(doubled_dot, 0, 0, DIR_FRAC)
    dut.resp_valid.value = 1
    await tick(dut)
    dut.resp_valid.value = 0

    # Multiply by the normal.
    received_request = False

    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)

    assert received_request, "No request after addition"
    assert int(dut.req_op.value) == 14, "Expected M_SCAL_VEC"
    assert int(dut.done.value) == 0, "Finished before multiplication answer"

    expected_scalar = pack_vec3(doubled_dot, 0, 0, DIR_FRAC) & 0xFFFF
    expected_vector = pack_vec3(*normal, DIR_FRAC)
    actual_u = int(dut.req_u.value) & 0xFFFF
    actual_v = int(dut.req_v.value)

    assert actual_u == expected_scalar, "Incorrect doubled dot product"
    assert actual_v == expected_vector, "Incorrect normal for multiplication"
    assert int(dut.req_fmt.value) == 1, "Expected DIR multiplication format"

    if test_handshake:
        await check_request_stall(dut)

    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0

    if test_handshake:
        await check_response_wait(dut)

    dut.resp_result.value = pack_vec3(*scaled_normal, DIR_FRAC)
    dut.resp_valid.value = 1
    await tick(dut)
    dut.resp_valid.value = 0

    # Subtract.
    received_request = False

    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)

    assert received_request, "No request after multiplication"
    assert int(dut.req_op.value) == 13, "Expected M_VSUB"
    assert int(dut.done.value) == 0, "Finished before subtraction answer"

    expected_u = pack_vec3(*direction, DIR_FRAC)
    expected_v = pack_vec3(*scaled_normal, DIR_FRAC)
    actual_u = int(dut.req_u.value)
    actual_v = int(dut.req_v.value)

    assert actual_u == expected_u, "Incorrect incoming direction for subtraction"
    assert actual_v == expected_v, "Incorrect scaled normal for subtraction"

    if test_handshake:
        await check_request_stall(dut)

    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0

    if test_handshake:
        await check_response_wait(dut)

    direction_written = False

    dut.resp_result.value = expected_direction
    dut.resp_valid.value = 1

    await Timer(1, unit="ns")

    if int(dut.d_we.value) == 1:
        assert int(dut.d_wdata.value) == expected_direction, "Incorrect reflected direction"
        direction_written = True

    await tick(dut)
    dut.resp_valid.value = 0

    # Multiply the normal by 0.03125 for the origin offset.
    received_request = False

    for i in range(MAX_CYCLES):
        if int(dut.d_we.value) == 1:
            assert int(dut.d_wdata.value) == expected_direction, "Incorrect reflected direction"
            direction_written = True

        if int(dut.req_valid.value) == 1:
            received_request = True
            break

        await tick(dut)

    assert received_request, "No request for origin offset"
    assert int(dut.req_op.value) == 14, "Expected M_SCAL_VEC"
    assert int(dut.done.value) == 0, "Finished before origin-offset answer"

    expected_scalar = pack_vec3(0.03125, 0, 0, POS_FRAC) & 0xFFFF
    expected_vector = pack_vec3(*normal, DIR_FRAC)
    actual_u = int(dut.req_u.value) & 0xFFFF
    actual_v = int(dut.req_v.value)

    assert actual_u == expected_scalar, "Incorrect origin-offset multiplier"
    assert actual_v == expected_vector, "Incorrect normal for origin offset"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for origin push-off"

    if test_handshake:
        await check_request_stall(dut)

    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0

    if test_handshake:
        await check_response_wait(dut)

    dut.resp_result.value = pack_vec3(*offset, POS_FRAC)
    dut.resp_valid.value = 1

    await Timer(1, unit="ns")

    if int(dut.d_we.value) == 1:
        assert int(dut.d_wdata.value) == expected_direction, "Incorrect reflected direction"
        direction_written = True

    await tick(dut)
    dut.resp_valid.value = 0

    # Add the offset to the original hit position.
    received_request = False

    for i in range(MAX_CYCLES):
        if int(dut.d_we.value) == 1:
            assert int(dut.d_wdata.value) == expected_direction, "Incorrect reflected direction"
            direction_written = True

        if int(dut.req_valid.value) == 1:
            received_request = True
            break

        await tick(dut)

    assert received_request, "No request to add the origin offset"
    assert int(dut.req_op.value) == 12, "Expected M_VADD"
    assert int(dut.done.value) == 0, "Finished before final addition answer"

    expected_o = pack_vec3(*origin, POS_FRAC)
    expected_offset = pack_vec3(*offset, POS_FRAC)
    actual_u = int(dut.req_u.value)
    actual_v = int(dut.req_v.value)

    assert ((actual_u == expected_o and actual_v == expected_offset) or (actual_u == expected_offset and actual_v == expected_o)), "Origin addition requested with incorrect position or offset"

    if test_handshake:
        await check_request_stall(dut)

    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0

    if test_handshake:
        await check_response_wait(dut)

    dut.resp_result.value = expected_origin
    dut.resp_valid.value = 1

    origin_written = False
    done_seen = False

    for i in range(MAX_CYCLES):
        await Timer(1, unit="ns")

        if int(dut.o_we.value) == 1:
            assert int(dut.o_wdata.value) == expected_origin, "Incorrect new origin"
            origin_written = True

        if int(dut.d_we.value) == 1:
            assert int(dut.d_wdata.value) == expected_direction, "Incorrect reflected direction"
            direction_written = True

        if int(dut.done.value) == 1:
            done_seen = True

        await tick(dut)
        dut.resp_valid.value = 0

        if done_seen:
            break

    assert done_seen, "Mirror operation never finished"
    assert direction_written, "Reflected direction was never written"
    assert origin_written, "New origin was never written"

    await Timer(1, unit="ns")
    assert int(dut.done.value) == 0, "done did not clear"



@cocotb.test()
async def test_mirror_head_on(dut):
    await run_mirror_case(
        dut,
        direction=(0, 0, -1),
        normal=(0, 0, 1),
        origin=(0, 0, 0),
    )


@cocotb.test()
async def test_mirror_angled(dut):
    await run_mirror_case(
        dut,
        direction=(0.6, 0, -0.8),
        normal=(0, 0, 1),
        origin=(0, 0, 0),
    )


@cocotb.test()
async def test_mirror_angled_other_side(dut):
    await run_mirror_case(
        dut,
        direction=(-0.6, 0, -0.8),
        normal=(0, 0, 1),
        origin=(0, 0, 0),
    )


@cocotb.test()
async def test_mirror_angle_in_x_and_y(dut):
    await run_mirror_case(
        dut,
        direction=(0.36, 0.48, -0.8),
        normal=(0, 0, 1),
        origin=(0, 0, 0),
    )


@cocotb.test()
async def test_mirror_facing_x(dut):
    await run_mirror_case(
        dut,
        direction=(-0.8, 0.6, 0),
        normal=(1, 0, 0),
        origin=(0, 0, 0),
    )


@cocotb.test()
async def test_mirror_facing_down(dut):
    await run_mirror_case(
        dut,
        direction=(0.6, 0, 0.8),
        normal=(0, 0, -1),
        origin=(0, 0, 0),
    )


@cocotb.test()
async def test_mirror_parallel(dut):
    # Arithmetic boundary case: D dot n = 0.
    await run_mirror_case(
        dut,
        direction=(1, 0, 0),
        normal=(0, 0, 1),
        origin=(0, 0, 0),
    )


@cocotb.test()
async def test_mirror_nonzero_origin(dut):
    await run_mirror_case(
        dut,
        direction=(0.6, 0, -0.8),
        normal=(0, 0, 1),
        origin=(2, -3, 5),
    )

@cocotb.test()
async def test_mirror_non_axis_normal_and_handshake(dut):
    # Also checks all six request stalls and delayed responses.
    await run_mirror_case(
        dut,
        direction=(0, 0, -1),
        normal=(0.6, 0, 0.8),
        origin=(1, -2, 3),
        test_handshake=True,
    )


# Matte / Ground - Secondary
# Small helpers for modelling the RTU responses; the request checks stay explicit.
def signed16(value):
    value &= 0xFFFF
    return value - 65536 if value >= 32768 else value

def fixed16(value):
    return max(-32768, min(32767, round(value * (1 << DIR_FRAC)))) & 0xFFFF

def float16(value):
    return signed16(value) / (1 << DIR_FRAC)

def components(packed):
    return tuple(float16(packed >> (16 * i)) for i in range(3))

def result_vec(values):
    return sum(fixed16(value) << (16 * i) for i, value in enumerate(values))

async def run_matte_case(dut, normal, origin, zero_sum=False, test_handshake=False):
    await setup(dut)
    dut.ray_o.value = pack_vec3(*origin, POS_FRAC)
    dut.ray_n.value = pack_vec3(*normal, DIR_FRAC)
    dut.mode.value = 1  # Matte and ground use the same mode.
    scratch = [0] * 7
    dut.start.value = 1
    await tick(dut)
    dut.start.value = 0

    # Phi = w * pi/2.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for phi = w * pi/2"
    assert int(dut.req_op.value) == 6, "Expected 6 for phi = w * pi/2"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for phi = w * pi/2"
    assert int(dut.done.value) == 0, "Finished before phi = w * pi/2 response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for phi = w * pi/2"
    w = int(dut.req_u.value) & 0xFFFF
    assert (w & 0x3F) == 0 and w <= 0x3FC0, "Invalid random w"
    assert (int(dut.req_v.value) & 0xFFFF) == 25736, "Wrong pi/2 constant"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    phi = fixed16(float16(w) * float16(25736))
    dut.resp_result.value = phi
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 1, "Incorrect scratch write for phi"
    assert int(dut.scratch_wdata.value) == (phi & 0xFFFF), "Incorrect scratch data for phi"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for phi"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for phi"
    assert int(dut.done.value) == 0, "Incorrect done for phi"
    await tick(dut)
    dut.resp_valid.value = 0
    scratch[0] = phi & 0xFFFF
    dut.scratch.value = sum(value << (16 * i) for i, value in enumerate(scratch))
    await Timer(1, unit="ns")

    # Z squared.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for z squared"
    assert int(dut.req_op.value) == 6, "Expected 6 for z squared"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for z squared"
    assert int(dut.done.value) == 0, "Finished before z squared response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for z squared"
    z = int(dut.req_u.value) & 0xFFFF
    assert (int(dut.req_v.value) & 0xFFFF) == z, "Z operands do not match"
    assert (z & 0x7F) == 0 and signed16(z) != -16384, "Invalid random z"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 2, "Expected scratch[1] write with Z request"
    assert int(dut.scratch_wdata.value) == z, "Incorrect Z scratch write"
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    scratch[1] = z
    dut.scratch.value = sum(value << (16 * i) for i, value in enumerate(scratch))
    z_squared = fixed16(float16(z) ** 2)
    dut.resp_result.value = z_squared
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for z squared"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for z squared"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for z squared"
    assert int(dut.done.value) == 0, "Incorrect done for z squared"
    await tick(dut)
    dut.resp_valid.value = 0
    await Timer(1, unit="ns")

    # One minus Z squared.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for one minus z squared"
    assert int(dut.req_op.value) == 1, "Expected 1 for one minus z squared"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for one minus z squared"
    assert int(dut.done.value) == 0, "Finished before one minus z squared response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for one minus z squared"
    assert (int(dut.req_u.value) & 0xFFFF) == 16384, "Wrong DIR one"
    assert (int(dut.req_v.value) & 0xFFFF) == z_squared, "Wrong Z squared operand"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    one_minus_z = fixed16(1 - float16(z_squared))
    dut.resp_result.value = one_minus_z
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for one minus z squared"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for one minus z squared"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for one minus z squared"
    assert int(dut.done.value) == 0, "Incorrect done for one minus z squared"
    await tick(dut)
    dut.resp_valid.value = 0
    await Timer(1, unit="ns")

    # Rho square root.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for rho square root"
    assert int(dut.req_op.value) == 8, "Expected 8 for rho square root"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for rho square root"
    assert int(dut.done.value) == 0, "Finished before rho square root response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for rho square root"
    assert (int(dut.req_u.value) & 0xFFFF) == one_minus_z, "Wrong sqrt operand"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    rho = fixed16(math.sqrt(max(0, float16(one_minus_z))))
    dut.resp_result.value = rho
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 4, "Incorrect scratch write for rho"
    assert int(dut.scratch_wdata.value) == (rho & 0xFFFF), "Incorrect scratch data for rho"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for rho"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for rho"
    assert int(dut.done.value) == 0, "Incorrect done for rho"
    await tick(dut)
    dut.resp_valid.value = 0
    scratch[2] = rho & 0xFFFF
    dut.scratch.value = sum(value << (16 * i) for i, value in enumerate(scratch))
    await Timer(1, unit="ns")

    # Rho times cos(phi).
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for rho times cos(phi)"
    assert int(dut.req_op.value) == 9, "Expected 9 for rho times cos(phi)"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for rho times cos(phi)"
    assert int(dut.done.value) == 0, "Finished before rho times cos(phi) response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for rho times cos(phi)"
    assert (int(dut.req_u.value) & 0xFFFF) == rho, "Wrong rho"
    assert (int(dut.req_v.value) & 0xFFFF) == phi, "Wrong phi"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    rcos = fixed16(float16(rho) * math.cos(float16(phi)))
    dut.resp_result.value = rcos
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 8, "Incorrect scratch write for rho cos"
    assert int(dut.scratch_wdata.value) == (rcos & 0xFFFF), "Incorrect scratch data for rho cos"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for rho cos"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for rho cos"
    assert int(dut.done.value) == 0, "Incorrect done for rho cos"
    await tick(dut)
    dut.resp_valid.value = 0
    scratch[3] = rcos & 0xFFFF
    dut.scratch.value = sum(value << (16 * i) for i, value in enumerate(scratch))
    await Timer(1, unit="ns")

    # Phi minus pi/2.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for phi minus pi/2"
    assert int(dut.req_op.value) == 1, "Expected 1 for phi minus pi/2"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for phi minus pi/2"
    assert int(dut.done.value) == 0, "Finished before phi minus pi/2 response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for phi minus pi/2"
    assert (int(dut.req_u.value) & 0xFFFF) == phi, "Wrong phi for subtraction"
    assert (int(dut.req_v.value) & 0xFFFF) == 25736, "Wrong pi/2"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    phi_minus = fixed16(float16(phi) - float16(25736))
    dut.resp_result.value = phi_minus
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for phi minus pi/2"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for phi minus pi/2"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for phi minus pi/2"
    assert int(dut.done.value) == 0, "Incorrect done for phi minus pi/2"
    await tick(dut)
    dut.resp_valid.value = 0
    await Timer(1, unit="ns")

    # Rho times sin(phi).
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for rho times sin(phi)"
    assert int(dut.req_op.value) == 9, "Expected 9 for rho times sin(phi)"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for rho times sin(phi)"
    assert int(dut.done.value) == 0, "Finished before rho times sin(phi) response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for rho times sin(phi)"
    assert (int(dut.req_u.value) & 0xFFFF) == rho, "Wrong rho for sine"
    assert (int(dut.req_v.value) & 0xFFFF) == phi_minus, "Wrong phi-pi/2"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    rsin = fixed16(float16(rho) * math.cos(float16(phi_minus)))
    dut.resp_result.value = rsin
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for rho sin"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for rho sin"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for rho sin"
    assert int(dut.done.value) == 0, "Incorrect done for rho sin"
    await tick(dut)
    dut.resp_valid.value = 0
    await Timer(1, unit="ns")

    # Add normal and random vector.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for add normal and random vector"
    assert int(dut.req_op.value) == 12, "Expected 12 for add normal and random vector"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for add normal and random vector"
    assert int(dut.done.value) == 0, "Finished before add normal and random vector response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for add normal and random vector"
    assert int(dut.req_u.value) == pack_vec3(*normal, DIR_FRAC), "Wrong surface normal"
    random_vector = int(dut.req_v.value)
    assert (random_vector & 0xFFFF) in (rcos, (~rcos & 0xFFFF)), "Incorrect random X"
    assert ((random_vector >> 16) & 0xFFFF) in (rsin, (~rsin & 0xFFFF)), "Incorrect random Y"
    assert ((random_vector >> 32) & 0xFFFF) == z, "Incorrect random Z"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    random_direction = components(random_vector)
    added = 0 if zero_sum else result_vec(tuple(n + r for n, r in zip(normal, random_direction)))
    dut.resp_result.value = added
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for n plus r"
    assert int(dut.d_we.value) == int(zero_sum), "Incorrect direction write enable for n plus r"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for n plus r"
    assert int(dut.done.value) == 0, "Incorrect done for n plus r"
    assert not zero_sum or int(dut.d_wdata.value) == pack_vec3(*normal, DIR_FRAC), "Zero sum wrote wrong normal"
    await tick(dut)
    dut.resp_valid.value = 0
    if zero_sum:
        dut.ray_d.value = pack_vec3(*normal, DIR_FRAC)
    await Timer(1, unit="ns")

    if not zero_sum:
        # Normalize matte direction.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for normalize matte direction"
        assert int(dut.req_op.value) == 17, "Expected 17 for normalize matte direction"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for normalize matte direction"
        assert int(dut.done.value) == 0, "Finished before normalize matte direction response"
        assert int(dut.req_resize.value) == 1, "Incorrect resize flag for normalize matte direction"
        assert int(dut.req_u.value) == added, "Wrong n+r vector for normalization"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        a, b, c = components(added)
        length = math.sqrt(a * a + b * b + c * c)
        normalized = result_vec((a / length, b / length, c / length))
        dut.resp_result.value = normalized
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for normalize matte"
        assert int(dut.d_we.value) == 1, "Incorrect direction write enable for normalize matte"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for normalize matte"
        assert int(dut.done.value) == 0, "Incorrect done for normalize matte"
        assert int(dut.d_wdata.value) == normalized, "Incorrect direction for normalize matte"
        await tick(dut)
        dut.resp_valid.value = 0
        dut.ray_d.value = normalized
        await Timer(1, unit="ns")

    # Push the origin away from the surface.
    # Push-off normal scale.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for push-off normal scale"
    assert int(dut.req_op.value) == 14, "Expected 14 for push-off normal scale"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for push-off normal scale"
    assert int(dut.done.value) == 0, "Finished before push-off normal scale response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for push-off normal scale"
    assert (int(dut.req_u.value) & 0xFFFF) == 4, "Wrong push-off scalar"
    assert int(dut.req_v.value) == pack_vec3(*normal, DIR_FRAC), "Wrong push-off normal"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    offset = pack_vec3(*(0.03125 * n for n in normal), POS_FRAC)
    dut.resp_result.value = offset
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for push-off scale"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for push-off scale"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for push-off scale"
    assert int(dut.done.value) == 0, "Incorrect done for push-off scale"
    await tick(dut)
    dut.resp_valid.value = 0
    await Timer(1, unit="ns")

    # Push-off origin add.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for push-off origin add"
    assert int(dut.req_op.value) == 12, "Expected 12 for push-off origin add"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for push-off origin add"
    assert int(dut.done.value) == 0, "Finished before push-off origin add response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for push-off origin add"
    assert int(dut.req_u.value) == pack_vec3(*origin, POS_FRAC), "Wrong hit position"
    assert int(dut.req_v.value) == offset, "Wrong origin offset"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    new_origin = pack_vec3(*(o + 0.03125 * n for o, n in zip(origin, normal)), POS_FRAC)
    dut.resp_result.value = new_origin
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for push-off origin"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for push-off origin"
    assert int(dut.o_we.value) == 1, "Incorrect origin write enable for push-off origin"
    assert int(dut.done.value) == 1, "Incorrect done for push-off origin"
    assert int(dut.o_wdata.value) == new_origin, "Incorrect origin for push-off origin"
    await tick(dut)
    dut.resp_valid.value = 0
    dut.ray_o.value = new_origin
    await Timer(1, unit="ns")

    assert int(dut.req_valid.value) == 0, "More requests after matte finished"

@cocotb.test()
async def test_matte_ground_normal(dut):
    await run_matte_case(dut, normal=(0, 0, 1), origin=(0, 0, 0), test_handshake=True)

@cocotb.test()
async def test_matte_ground_nonzero_origin(dut):
    await run_matte_case(dut, normal=(0, 1, 0), origin=(2, -3, 5))

@cocotb.test()
async def test_matte_ground_zero_vector(dut):
    await run_matte_case(dut, normal=(0, 0, 1), origin=(1, 2, 3), zero_sum=True)


# Glass - Secondary
async def run_glass_case(dut, direction, normal, origin, flip=False, path="refract", test_handshake=False):
    await setup(dut)
    dut.ray_o.value = pack_vec3(*origin, POS_FRAC)
    dut.ray_d.value = pack_vec3(*direction, DIR_FRAC)
    dut.ray_n.value = pack_vec3(*normal, DIR_FRAC)
    dut.flip.value = int(flip)
    dut.mode.value = 3
    scratch = [0] * 7
    dut.start.value = 1
    await tick(dut)
    dut.start.value = 0

    # Direction dot normal.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for direction dot normal"
    assert int(dut.req_op.value) == 15, "Expected 15 for direction dot normal"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for direction dot normal"
    assert int(dut.done.value) == 0, "Finished before direction dot normal response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for direction dot normal"
    assert int(dut.req_u.value) == pack_vec3(*direction, DIR_FRAC), "Incorrect incoming direction"
    assert int(dut.req_v.value) == pack_vec3(*normal, DIR_FRAC), "Incorrect surface normal"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    dot = fixed16(sum(d * n for d, n in zip(components(pack_vec3(*direction, DIR_FRAC)), components(pack_vec3(*normal, DIR_FRAC)))))
    dut.resp_result.value = dot
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 1, "Incorrect scratch write for glass dot"
    assert int(dut.scratch_wdata.value) == (dot & 0xFFFF), "Incorrect scratch data for glass dot"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass dot"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass dot"
    assert int(dut.done.value) == 0, "Incorrect done for glass dot"
    await tick(dut)
    dut.resp_valid.value = 0
    scratch[0] = dot & 0xFFFF
    dut.scratch.value = sum(value << (16 * i) for i, value in enumerate(scratch))
    await Timer(1, unit="ns")

    # Cosine theta.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for cosine theta"
    assert int(dut.req_op.value) == 1, "Expected 1 for cosine theta"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for cosine theta"
    assert int(dut.done.value) == 0, "Finished before cosine theta response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for cosine theta"
    assert (int(dut.req_u.value) & 0xFFFF) == 0, "Wrong zero operand"
    assert (int(dut.req_v.value) & 0xFFFF) == dot, "Wrong dot operand"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    cosine = fixed16(-float16(dot))
    dut.resp_result.value = cosine
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 2, "Incorrect scratch write for glass cosine"
    assert int(dut.scratch_wdata.value) == (cosine & 0xFFFF), "Incorrect scratch data for glass cosine"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass cosine"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass cosine"
    assert int(dut.done.value) == 0, "Incorrect done for glass cosine"
    await tick(dut)
    dut.resp_valid.value = 0
    scratch[1] = cosine & 0xFFFF
    dut.scratch.value = sum(value << (16 * i) for i, value in enumerate(scratch))
    await Timer(1, unit="ns")

    # Cosine squared.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for cosine squared"
    assert int(dut.req_op.value) == 6, "Expected 6 for cosine squared"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for cosine squared"
    assert int(dut.done.value) == 0, "Finished before cosine squared response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for cosine squared"
    assert (int(dut.req_u.value) & 0xFFFF) == cosine, "Wrong cosine u"
    assert (int(dut.req_v.value) & 0xFFFF) == cosine, "Wrong cosine v"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    cosine_squared = fixed16(float16(cosine) ** 2)
    dut.resp_result.value = cosine_squared
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass cosine squared"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass cosine squared"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass cosine squared"
    assert int(dut.done.value) == 0, "Incorrect done for glass cosine squared"
    await tick(dut)
    dut.resp_valid.value = 0
    await Timer(1, unit="ns")

    # One minus cosine squared.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for one minus cosine squared"
    assert int(dut.req_op.value) == 1, "Expected 1 for one minus cosine squared"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for one minus cosine squared"
    assert int(dut.done.value) == 0, "Finished before one minus cosine squared response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for one minus cosine squared"
    assert (int(dut.req_u.value) & 0xFFFF) == 16384, "Wrong DIR one"
    assert (int(dut.req_v.value) & 0xFFFF) == cosine_squared, "Wrong cosine squared"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    sin_squared = fixed16(1 - float16(cosine_squared))
    dut.resp_result.value = sin_squared
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass sin squared"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass sin squared"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass sin squared"
    assert int(dut.done.value) == 0, "Incorrect done for glass sin squared"
    await tick(dut)
    dut.resp_valid.value = 0
    await Timer(1, unit="ns")

    # Eta times sin squared.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for eta times sin squared"
    assert int(dut.req_op.value) == 6, "Expected 6 for eta times sin squared"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for eta times sin squared"
    assert int(dut.done.value) == 0, "Finished before eta times sin squared response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for eta times sin squared"
    eta = 24576 if flip else 10923
    assert (int(dut.req_u.value) & 0xFFFF) == eta, "Wrong refraction ratio"
    assert (int(dut.req_v.value) & 0xFFFF) == sin_squared, "Wrong sin squared"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    eta_sin = fixed16(float16(eta) * float16(sin_squared))
    dut.resp_result.value = eta_sin
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for eta sin squared"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for eta sin squared"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for eta sin squared"
    assert int(dut.done.value) == 0, "Incorrect done for eta sin squared"
    await tick(dut)
    dut.resp_valid.value = 0
    await Timer(1, unit="ns")

    # Eta squared times sin squared.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for eta squared times sin squared"
    assert int(dut.req_op.value) == 6, "Expected 6 for eta squared times sin squared"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for eta squared times sin squared"
    assert int(dut.done.value) == 0, "Finished before eta squared times sin squared response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for eta squared times sin squared"
    assert (int(dut.req_u.value) & 0xFFFF) == eta, "Wrong eta"
    assert (int(dut.req_v.value) & 0xFFFF) == eta_sin, "Wrong eta sin"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    eta_squared_sin = fixed16(float16(eta) * float16(eta_sin))
    dut.resp_result.value = eta_squared_sin
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for eta squared sin squared"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for eta squared sin squared"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for eta squared sin squared"
    assert int(dut.done.value) == 0, "Incorrect done for eta squared sin squared"
    await tick(dut)
    dut.resp_valid.value = 0
    await Timer(1, unit="ns")

    # K discriminant.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for k discriminant"
    assert int(dut.req_op.value) == 1, "Expected 1 for k discriminant"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for k discriminant"
    assert int(dut.done.value) == 0, "Finished before k discriminant response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for k discriminant"
    assert (int(dut.req_u.value) & 0xFFFF) == 16384, "Wrong DIR one"
    assert (int(dut.req_v.value) & 0xFFFF) == eta_squared_sin, "Wrong eta squared sin squared"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    k = fixed16(1 - float16(eta_squared_sin))
    dut.resp_result.value = k
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 4, "Incorrect scratch write for glass k"
    assert int(dut.scratch_wdata.value) == (k & 0xFFFF), "Incorrect scratch data for glass k"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass k"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass k"
    assert int(dut.done.value) == 0, "Incorrect done for glass k"
    await tick(dut)
    dut.resp_valid.value = 0
    scratch[2] = k & 0xFFFF
    dut.scratch.value = sum(value << (16 * i) for i, value in enumerate(scratch))
    await Timer(1, unit="ns")

    if path != "tir":
        # One minus cosine.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for one minus cosine"
        assert int(dut.req_op.value) == 1, "Expected 1 for one minus cosine"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for one minus cosine"
        assert int(dut.done.value) == 0, "Finished before one minus cosine response"
        assert int(dut.req_resize.value) == 0, "Incorrect resize flag for one minus cosine"
        assert (int(dut.req_u.value) & 0xFFFF) == 16384, "Wrong DIR one"
        assert (int(dut.req_v.value) & 0xFFFF) == cosine, "Wrong cosine"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        x = fixed16(1 - float16(cosine))
        dut.resp_result.value = x
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 8, "Incorrect scratch write for glass 1-cosine"
        assert int(dut.scratch_wdata.value) == (x & 0xFFFF), "Incorrect scratch data for glass 1-cosine"
        assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass 1-cosine"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass 1-cosine"
        assert int(dut.done.value) == 0, "Incorrect done for glass 1-cosine"
        await tick(dut)
        dut.resp_valid.value = 0
        scratch[3] = x & 0xFFFF
        dut.scratch.value = sum(value << (16 * i) for i, value in enumerate(scratch))
        await Timer(1, unit="ns")

        # Schlick X squared.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for schlick x squared"
        assert int(dut.req_op.value) == 6, "Expected 6 for schlick x squared"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for schlick x squared"
        assert int(dut.done.value) == 0, "Finished before schlick x squared response"
        assert int(dut.req_resize.value) == 0, "Incorrect resize flag for schlick x squared"
        assert (int(dut.req_u.value) & 0xFFFF) == x, "Wrong x operand"
        assert (int(dut.req_v.value) & 0xFFFF) == x, "Wrong x operand"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        x2 = fixed16(float16(x) ** 2)
        dut.resp_result.value = x2
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass x squared"
        assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass x squared"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass x squared"
        assert int(dut.done.value) == 0, "Incorrect done for glass x squared"
        await tick(dut)
        dut.resp_valid.value = 0
        await Timer(1, unit="ns")

        # Schlick X fourth.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for schlick x fourth"
        assert int(dut.req_op.value) == 6, "Expected 6 for schlick x fourth"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for schlick x fourth"
        assert int(dut.done.value) == 0, "Finished before schlick x fourth response"
        assert int(dut.req_resize.value) == 0, "Incorrect resize flag for schlick x fourth"
        assert (int(dut.req_u.value) & 0xFFFF) == x2, "Wrong x2 operand"
        assert (int(dut.req_v.value) & 0xFFFF) == x2, "Wrong x2 operand"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        x4 = fixed16(float16(x2) ** 2)
        dut.resp_result.value = x4
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass x fourth"
        assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass x fourth"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass x fourth"
        assert int(dut.done.value) == 0, "Incorrect done for glass x fourth"
        await tick(dut)
        dut.resp_valid.value = 0
        await Timer(1, unit="ns")

        # Schlick X fifth.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for schlick x fifth"
        assert int(dut.req_op.value) == 6, "Expected 6 for schlick x fifth"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for schlick x fifth"
        assert int(dut.done.value) == 0, "Finished before schlick x fifth response"
        assert int(dut.req_resize.value) == 0, "Incorrect resize flag for schlick x fifth"
        assert (int(dut.req_u.value) & 0xFFFF) == x4, "Wrong x4 operand"
        assert (int(dut.req_v.value) & 0xFFFF) == x, "Wrong x operand"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        x5 = fixed16(float16(x4) * float16(x))
        dut.resp_result.value = x5
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass x fifth"
        assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass x fifth"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass x fifth"
        assert int(dut.done.value) == 0, "Incorrect done for glass x fifth"
        await tick(dut)
        dut.resp_valid.value = 0
        await Timer(1, unit="ns")

        # Schlick scale.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for schlick scale"
        assert int(dut.req_op.value) == 6, "Expected 6 for schlick scale"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for schlick scale"
        assert int(dut.done.value) == 0, "Finished before schlick scale response"
        assert int(dut.req_resize.value) == 0, "Incorrect resize flag for schlick scale"
        assert (int(dut.req_u.value) & 0xFFFF) == x5, "Wrong x5 operand"
        assert (int(dut.req_v.value) & 0xFFFF) == 15729, "Wrong 0.96 constant"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        schlick = fixed16(float16(x5) * float16(15729))
        dut.resp_result.value = schlick
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass schlick scale"
        assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass schlick scale"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass schlick scale"
        assert int(dut.done.value) == 0, "Incorrect done for glass schlick scale"
        await tick(dut)
        dut.resp_valid.value = 0
        await Timer(1, unit="ns")

        # Schlick reflectance.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for schlick reflectance"
        assert int(dut.req_op.value) == 0, "Expected 0 for schlick reflectance"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for schlick reflectance"
        assert int(dut.done.value) == 0, "Finished before schlick reflectance response"
        assert int(dut.req_resize.value) == 0, "Incorrect resize flag for schlick reflectance"
        assert (int(dut.req_u.value) & 0xFFFF) == schlick, "Wrong Schlick term"
        assert (int(dut.req_v.value) & 0xFFFF) == 655, "Wrong R0"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        reflectance = fixed16(float16(schlick) + float16(655))
        dut.resp_result.value = reflectance
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass reflectance"
        assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass reflectance"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass reflectance"
        assert int(dut.done.value) == 0, "Incorrect done for glass reflectance"
        await tick(dut)
        dut.resp_valid.value = 0
        await Timer(1, unit="ns")

        # Schlick compare.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for schlick compare"
        assert int(dut.req_op.value) == 1, "Expected 1 for schlick compare"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for schlick compare"
        assert int(dut.done.value) == 0, "Finished before schlick compare response"
        assert int(dut.req_resize.value) == 0, "Incorrect resize flag for schlick compare"
        rand = int(dut.req_u.value) & 0xFFFF
        assert (rand & 0x3F) == 0 and rand <= 0x3FC0, "Invalid Schlick RNG value"
        assert (int(dut.req_v.value) & 0xFFFF) == reflectance, "Wrong reflection threshold"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        # Force the Schlick comparison response to exercise reflection and refraction branches.
        # This checks branch control, not the arithmetic result of random minus reflectance.
        compare_result = fixed16(-0.1 if path == "reflect" else 0.1)
        dut.resp_result.value = compare_result
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass comparison"
        assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass comparison"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass comparison"
        assert int(dut.done.value) == 0, "Incorrect done for glass comparison"
        await tick(dut)
        dut.resp_valid.value = 0
        await Timer(1, unit="ns")

    if path in ("tir", "reflect"):
        # Reflection dot doubled.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for reflection dot doubled"
        assert int(dut.req_op.value) == 0, "Expected 0 for reflection dot doubled"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for reflection dot doubled"
        assert int(dut.done.value) == 0, "Finished before reflection dot doubled response"
        assert int(dut.req_resize.value) == 0, "Incorrect resize flag for reflection dot doubled"
        assert (int(dut.req_u.value) & 0xFFFF) == dot, "Wrong stored dot"
        assert (int(dut.req_v.value) & 0xFFFF) == dot, "Wrong stored dot"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        doubled_dot = fixed16(2 * float16(dot))
        dut.resp_result.value = doubled_dot
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass reflection double dot"
        assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass reflection double dot"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass reflection double dot"
        assert int(dut.done.value) == 0, "Incorrect done for glass reflection double dot"
        await tick(dut)
        dut.resp_valid.value = 0
        await Timer(1, unit="ns")

        # Reflection scale normal.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for reflection scale normal"
        assert int(dut.req_op.value) == 14, "Expected 14 for reflection scale normal"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for reflection scale normal"
        assert int(dut.done.value) == 0, "Finished before reflection scale normal response"
        assert int(dut.req_resize.value) == 0, "Incorrect resize flag for reflection scale normal"
        assert (int(dut.req_u.value) & 0xFFFF) == doubled_dot, "Wrong doubled dot"
        assert int(dut.req_v.value) == pack_vec3(*normal, DIR_FRAC), "Wrong normal"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        scaled_normal = result_vec(tuple(float16(doubled_dot) * n for n in components(pack_vec3(*normal, DIR_FRAC))))
        dut.resp_result.value = scaled_normal
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass reflection scale"
        assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass reflection scale"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass reflection scale"
        assert int(dut.done.value) == 0, "Incorrect done for glass reflection scale"
        await tick(dut)
        dut.resp_valid.value = 0
        await Timer(1, unit="ns")

        # Reflection subtraction.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for reflection subtraction"
        assert int(dut.req_op.value) == 13, "Expected 13 for reflection subtraction"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for reflection subtraction"
        assert int(dut.done.value) == 0, "Finished before reflection subtraction response"
        assert int(dut.req_resize.value) == 0, "Incorrect resize flag for reflection subtraction"
        assert int(dut.req_u.value) == pack_vec3(*direction, DIR_FRAC), "Wrong incoming direction"
        assert int(dut.req_v.value) == scaled_normal, "Wrong scaled normal"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        reflected = result_vec(tuple(d - n for d, n in zip(components(pack_vec3(*direction, DIR_FRAC)), components(scaled_normal))))
        dut.resp_result.value = reflected
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass reflected direction"
        assert int(dut.d_we.value) == 1, "Incorrect direction write enable for glass reflected direction"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass reflected direction"
        assert int(dut.done.value) == 0, "Incorrect done for glass reflected direction"
        assert int(dut.d_wdata.value) == reflected, "Incorrect direction for glass reflected direction"
        await tick(dut)
        dut.resp_valid.value = 0
        dut.ray_d.value = reflected
        await Timer(1, unit="ns")

    else:
        # Refraction eta times direction.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for refraction eta times direction"
        assert int(dut.req_op.value) == 14, "Expected 14 for refraction eta times direction"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for refraction eta times direction"
        assert int(dut.done.value) == 0, "Finished before refraction eta times direction response"
        assert int(dut.req_resize.value) == 0, "Incorrect resize flag for refraction eta times direction"
        assert (int(dut.req_u.value) & 0xFFFF) == eta, "Wrong eta"
        assert int(dut.req_v.value) == pack_vec3(*direction, DIR_FRAC), "Wrong initial direction"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        eta_direction = result_vec(tuple(float16(eta) * d for d in components(pack_vec3(*direction, DIR_FRAC))))
        dut.resp_result.value = eta_direction
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass eta times direction"
        assert int(dut.d_we.value) == 1, "Incorrect direction write enable for glass eta times direction"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass eta times direction"
        assert int(dut.done.value) == 0, "Incorrect done for glass eta times direction"
        assert int(dut.d_wdata.value) == eta_direction, "Incorrect direction for glass eta times direction"
        await tick(dut)
        dut.resp_valid.value = 0
        dut.ray_d.value = eta_direction
        await Timer(1, unit="ns")

        # Refraction square root K.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for refraction square root k"
        assert int(dut.req_op.value) == 8, "Expected 8 for refraction square root k"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for refraction square root k"
        assert int(dut.done.value) == 0, "Finished before refraction square root k response"
        assert int(dut.req_resize.value) == 0, "Incorrect resize flag for refraction square root k"
        assert (int(dut.req_u.value) & 0xFFFF) == k, "Wrong K"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        sqrt_k = fixed16(math.sqrt(float16(k)))
        dut.resp_result.value = sqrt_k
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 16, "Incorrect scratch write for glass sqrt k"
        assert int(dut.scratch_wdata.value) == (sqrt_k & 0xFFFF), "Incorrect scratch data for glass sqrt k"
        assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass sqrt k"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass sqrt k"
        assert int(dut.done.value) == 0, "Incorrect done for glass sqrt k"
        await tick(dut)
        dut.resp_valid.value = 0
        scratch[4] = sqrt_k & 0xFFFF
        dut.scratch.value = sum(value << (16 * i) for i, value in enumerate(scratch))
        await Timer(1, unit="ns")

        # Refraction eta times cosine.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for refraction eta times cosine"
        assert int(dut.req_op.value) == 6, "Expected 6 for refraction eta times cosine"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for refraction eta times cosine"
        assert int(dut.done.value) == 0, "Finished before refraction eta times cosine response"
        assert int(dut.req_resize.value) == 0, "Incorrect resize flag for refraction eta times cosine"
        assert (int(dut.req_u.value) & 0xFFFF) == eta, "Wrong eta"
        assert (int(dut.req_v.value) & 0xFFFF) == cosine, "Wrong cosine"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        eta_cosine = fixed16(float16(eta) * float16(cosine))
        dut.resp_result.value = eta_cosine
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass eta cosine"
        assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass eta cosine"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass eta cosine"
        assert int(dut.done.value) == 0, "Incorrect done for glass eta cosine"
        await tick(dut)
        dut.resp_valid.value = 0
        await Timer(1, unit="ns")

        # Refraction coefficient.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for refraction coefficient"
        assert int(dut.req_op.value) == 1, "Expected 1 for refraction coefficient"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for refraction coefficient"
        assert int(dut.done.value) == 0, "Finished before refraction coefficient response"
        assert int(dut.req_resize.value) == 0, "Incorrect resize flag for refraction coefficient"
        assert (int(dut.req_u.value) & 0xFFFF) == eta_cosine, "Wrong eta cosine"
        assert (int(dut.req_v.value) & 0xFFFF) == sqrt_k, "Wrong sqrt K"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        coefficient = fixed16(float16(eta_cosine) - float16(sqrt_k))
        dut.resp_result.value = coefficient
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass coefficient"
        assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass coefficient"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass coefficient"
        assert int(dut.done.value) == 0, "Incorrect done for glass coefficient"
        await tick(dut)
        dut.resp_valid.value = 0
        await Timer(1, unit="ns")

        # Refraction coefficient times normal.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for refraction coefficient times normal"
        assert int(dut.req_op.value) == 14, "Expected 14 for refraction coefficient times normal"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for refraction coefficient times normal"
        assert int(dut.done.value) == 0, "Finished before refraction coefficient times normal response"
        assert int(dut.req_resize.value) == 0, "Incorrect resize flag for refraction coefficient times normal"
        assert (int(dut.req_u.value) & 0xFFFF) == coefficient, "Wrong coefficient"
        assert int(dut.req_v.value) == pack_vec3(*normal, DIR_FRAC), "Wrong normal"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        scaled_normal = result_vec(tuple(float16(coefficient) * n for n in components(pack_vec3(*normal, DIR_FRAC))))
        dut.resp_result.value = scaled_normal
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass refraction normal scale"
        assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass refraction normal scale"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass refraction normal scale"
        assert int(dut.done.value) == 0, "Incorrect done for glass refraction normal scale"
        await tick(dut)
        dut.resp_valid.value = 0
        await Timer(1, unit="ns")

        # Refraction direction addition.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for refraction direction addition"
        assert int(dut.req_op.value) == 12, "Expected 12 for refraction direction addition"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for refraction direction addition"
        assert int(dut.done.value) == 0, "Finished before refraction direction addition response"
        assert int(dut.req_resize.value) == 0, "Incorrect resize flag for refraction direction addition"
        assert int(dut.req_u.value) == eta_direction, "Wrong stored eta D"
        assert int(dut.req_v.value) == scaled_normal, "Wrong coefficient normal"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        unnormalized = result_vec(tuple(a + b for a, b in zip(components(eta_direction), components(scaled_normal))))
        dut.resp_result.value = unnormalized
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass direction sum"
        assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass direction sum"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass direction sum"
        assert int(dut.done.value) == 0, "Incorrect done for glass direction sum"
        await tick(dut)
        dut.resp_valid.value = 0
        await Timer(1, unit="ns")

        # Refraction normalize.
        received_request = False
        for i in range(MAX_CYCLES):
            if int(dut.req_valid.value) == 1:
                received_request = True
                break
            await tick(dut)
        assert received_request, "No request for refraction normalize"
        assert int(dut.req_op.value) == 17, "Expected 17 for refraction normalize"
        assert int(dut.req_fmt.value) == 1, "Expected DIR format for refraction normalize"
        assert int(dut.done.value) == 0, "Finished before refraction normalize response"
        assert int(dut.req_resize.value) == 1, "Incorrect resize flag for refraction normalize"
        assert int(dut.req_u.value) == unnormalized, "Wrong sum for normalization"
        if test_handshake:
            await check_request_stall(dut)
        dut.req_ready.value = 1
        await tick(dut)
        dut.req_ready.value = 0
        if test_handshake:
            await check_response_wait(dut)

        a, b, c = components(unnormalized)
        length = math.sqrt(a * a + b * b + c * c)
        refracted = result_vec((a / length, b / length, c / length))
        dut.resp_result.value = refracted
        dut.resp_valid.value = 1
        await Timer(1, unit="ns")
        assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass refracted direction"
        assert int(dut.d_we.value) == 1, "Incorrect direction write enable for glass refracted direction"
        assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass refracted direction"
        assert int(dut.done.value) == 0, "Incorrect done for glass refracted direction"
        assert int(dut.d_wdata.value) == refracted, "Incorrect direction for glass refracted direction"
        await tick(dut)
        dut.resp_valid.value = 0
        dut.ray_d.value = refracted
        await Timer(1, unit="ns")

    # Glass push-off scale.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for glass push-off scale"
    assert int(dut.req_op.value) == 14, "Expected 14 for glass push-off scale"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for glass push-off scale"
    assert int(dut.done.value) == 0, "Finished before glass push-off scale response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for glass push-off scale"
    push_scalar = 4 if path in ("tir", "reflect") else 0xFFFC
    assert (int(dut.req_u.value) & 0xFFFF) == push_scalar, "Wrong signed push-off scalar"
    assert int(dut.req_v.value) == pack_vec3(*normal, DIR_FRAC), "Wrong push-off normal"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    sign = 1 if path in ("tir", "reflect") else -1
    offset = pack_vec3(*(sign * 0.03125 * n for n in normal), POS_FRAC)
    dut.resp_result.value = offset
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass push-off scale"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass push-off scale"
    assert int(dut.o_we.value) == 0, "Incorrect origin write enable for glass push-off scale"
    assert int(dut.done.value) == 0, "Incorrect done for glass push-off scale"
    await tick(dut)
    dut.resp_valid.value = 0
    await Timer(1, unit="ns")

    # Glass push-off origin addition.
    received_request = False
    for i in range(MAX_CYCLES):
        if int(dut.req_valid.value) == 1:
            received_request = True
            break
        await tick(dut)
    assert received_request, "No request for glass push-off origin addition"
    assert int(dut.req_op.value) == 12, "Expected 12 for glass push-off origin addition"
    assert int(dut.req_fmt.value) == 1, "Expected DIR format for glass push-off origin addition"
    assert int(dut.done.value) == 0, "Finished before glass push-off origin addition response"
    assert int(dut.req_resize.value) == 0, "Incorrect resize flag for glass push-off origin addition"
    assert int(dut.req_u.value) == pack_vec3(*origin, POS_FRAC), "Wrong hit point"
    assert int(dut.req_v.value) == offset, "Wrong origin offset"
    if test_handshake:
        await check_request_stall(dut)
    dut.req_ready.value = 1
    await tick(dut)
    dut.req_ready.value = 0
    if test_handshake:
        await check_response_wait(dut)

    new_origin = pack_vec3(*(o + sign * 0.03125 * n for o, n in zip(origin, normal)), POS_FRAC)
    dut.resp_result.value = new_origin
    dut.resp_valid.value = 1
    await Timer(1, unit="ns")
    assert int(dut.scratch_we.value) == 0, "Incorrect scratch write for glass new origin"
    assert int(dut.d_we.value) == 0, "Incorrect direction write enable for glass new origin"
    assert int(dut.o_we.value) == 1, "Incorrect origin write enable for glass new origin"
    assert int(dut.done.value) == 1, "Incorrect done for glass new origin"
    assert int(dut.o_wdata.value) == new_origin, "Incorrect origin for glass new origin"
    await tick(dut)
    dut.resp_valid.value = 0
    dut.ray_o.value = new_origin
    await Timer(1, unit="ns")

    assert int(dut.req_valid.value) == 0, "More requests after glass finished"

@cocotb.test()
async def test_glass_enter_refract(dut):
    await run_glass_case(dut, direction=(0.6, 0, -0.8), normal=(0, 0, 1), origin=(0, 0, 0), path="refract", test_handshake=True)

@cocotb.test()
async def test_glass_exit_refract(dut):
    await run_glass_case(dut, direction=(0.28, 0, -0.96), normal=(0, 0, 1), origin=(1, 2, 3), flip=True, path="refract")

@cocotb.test()
async def test_glass_total_internal_reflection(dut):
    await run_glass_case(dut, direction=(0.8, 0, -0.6), normal=(0, 0, 1), origin=(1, -2, 3), flip=True, path="tir")

@cocotb.test()
async def test_glass_schlick_reflection(dut):
    await run_glass_case(dut, direction=(1, 0, 0), normal=(0, 0, 1), origin=(0, 0, 0), path="reflect")

