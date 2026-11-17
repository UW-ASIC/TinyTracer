# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer, RisingEdge, ReadOnly

from test_decode_invariants import STATE_DECODE, reset_dut, set_rom_addr

@cocotb.test()
async def test_rom_functionality(dut):
    """tests that ROM address zero returns the first VADD micro operation"""

    dut._log.info("Testing rom functionality")
    decode = dut.dut

    decode.curr_addr.value = 0
    await Timer(1, units="ns")

    assert decode.micro_op_word == 0x0030 and decode.barrier == 0


# 3. Instruction Decode and ROM Tests

@cocotb.test()
async def test_scalar_macro_conversion(dut):
    """tests that each scalar macro op is converted into the correct micro op"""

    dut._log.info("Testing scalar macro conversion...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    decode = dut.dut

    scalar_ops = [
        0b00000, # ADD
        0b00001, # SUB
        0b00010, # EQ
        0b00011, # NE
        0b00100, # LT
        0b00101, # GE
        0b00110, # MUL
        0b00111, # DIV
        0b01000, # SQRT
        0b01001, # COS
        0b01011  # MAG
    ]

    for opcode in scalar_ops:
        # reset before testing each opcode
        await reset_dut(dut)

        dut.macro_opcode.value = opcode
        dut.macro_u_x.value = 0x1234
        dut.macro_v_x.value = 0x5678
        dut.macro_req_valid.value = 1

        await Timer(1, units="ns")

        assert int(decode.state.value) == STATE_DECODE

        assert int(dut.micro_req_valid.value) == 1
        assert int(dut.micro_req_direct.value) == 1
        assert int(dut.micro_req_u1.value) == 0x1234
        assert int(dut.micro_req_v1.value) == 0x5678

        expected_micro_word = opcode & 0xF
        assert int(dut.micro_req_op.value) == expected_micro_word

        dut.macro_req_valid.value = 0


@cocotb.test()
async def test_vector_rom_ranges(dut):
    """tests that each vector macro op selects the correct ROM range"""

    dut._log.info("Testing vector ROM ranges...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    vector_ranges = [
        (0b01100, 0, 3),
        (0b01101, 3, 6),
        (0b01110, 6, 9),
        (0b01111, 9, 14),
        (0b10000, 14, 23),
        (0b10001, 23, 29),
        (0b10010, 29, 32),
        (0b10011, 32, 35),
    ]

    for opcode, start_addr, end_addr in vector_ranges:
        await reset_dut(dut)

        dut.micro_req_ready.value = 0
        dut.macro_opcode.value = opcode
        dut.macro_req_valid.value = 1

        await Timer(1, units="ns")
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

        assert int(decode.curr_addr.value) == start_addr
        assert int(decode.op_addr_end.value) == end_addr

        dut.macro_req_valid.value = 0


@cocotb.test()
async def test_vector_format_capture_and_retention(dut):
    """tests that a vector macro keeps its accepted format throughout dispatch"""

    dut._log.info("Testing vector format capture and retention...")

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    decode = dut.dut

    # tinytracer_pkg defines FMT_POS as 0 and FMT_DIR as 1
    for fmt in (0, 1):
        await reset_dut(dut)
        await Timer(1, units="ns")

        # accept VMUL with the selected format
        dut.macro_opcode.value = 0b10011
        dut.macro_fmt.value = fmt
        dut.macro_req_valid.value = 1
        await Timer(1, units="ns")

        assert int(decode.macro_accept.value) == 1

        await RisingEdge(dut.clk)
        await Timer(1, units="ns")

        assert int(decode.state.value) == 0b01
        assert int(decode.curr_addr.value) == 32
        assert int(decode.fmt_reg.value) == fmt

        # change the unused macro input while dispatch uses the stored format
        dut.macro_req_valid.value = 0
        dut.macro_fmt.value = 1 - fmt
        dut.micro_req_ready.value = 1
        await Timer(1, units="ns")

        for issued in range(3):
            assert int(decode.macro_accept.value) == 0
            assert int(decode.fmt_reg.value) == fmt
            assert int(dut.micro_req_valid.value) == 1
            assert int(decode.micro_issue.value) == 1

            await RisingEdge(dut.clk)
            await Timer(1, units="ns")

            assert int(decode.curr_addr.value) == 33 + issued
            assert int(decode.state.value) == 0b01
            assert int(decode.fmt_reg.value) == fmt


@cocotb.test()
async def test_rom_contents(dut):
    """tests the complete ROM instruction contents"""

    dut._log.info("Testing complete ROM contents...")

    decode = dut.dut

    expected = [
        (0,  0x0030, 0),
        (1,  0x04C0, 0),
        (2,  0x0950, 0),

        (3,  0x0031, 0),
        (4,  0x04C1, 0),
        (5,  0x0951, 0),

        (6,  0x0446, 0),
        (7,  0x0856, 0),
        (8,  0x0036, 0),

        (9,  0x0036, 0),
        (10, 0x04C6, 0),
        (11, 0x0956, 0),
        (12, 0x0010, 1),
        (13, 0x0020, 1),

        (14, 0x1946, 0),
        (15, 0x0936, 0),
        (16, 0x1046, 0),
        (17, 0x0CB6, 0),
        (18, 0x04D6, 0),
        (19, 0x1456, 0),
        (20, 0x00E1, 1),
        (21, 0x0551, 0),
        (22, 0x0A31, 0),

        (23, 0x101B, 0),
        (24, 0x122B, 1),
        (25, 0x11C7, 1),
        (26, 0x0206, 1),
        (27, 0x0616, 0),
        (28, 0x0A26, 0),

        (29, 0x0607, 0),
        (30, 0x0A87, 0),
        (31, 0x0187, 0),

        (32, 0x0036, 0),
        (33, 0x04C6, 0),
        (34, 0x0956, 0),
    ]

    for addr, micro_op, barrier in expected:
        await set_rom_addr(decode, addr)

        assert int(decode.micro_op_word.value) == micro_op
        assert int(decode.barrier.value) == barrier


@cocotb.test()
async def test_rom_default_entry(dut):
    """tests that an unused read-only memory address returns an empty non-barrier micro-operation."""

    dut._log.info("Testing unused ROM entry...")

    decode = dut.dut

    # read only
    await set_rom_addr(decode, 63)

    assert int(decode.micro_op_word.value) == 0
    assert int(decode.barrier.value) == 0

