import cocotb
from cocotb.triggers import Timer

from reference_models.alu import (
    alu_ref, ALU_ADD, ALU_SUB,
    ALU_EQ, ALU_NE, ALU_LT, ALU_GE
)


async def reset(dut):
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.req_valid.value = 0
    dut.req_op1.value = 0
    dut.req_op2.value = 0
    dut.req_opcode.value = 0

    await Timer(5, units="ns")
    dut.clk.value = 1
    await Timer(5, units="ns")

    dut.clk.value = 0
    dut.rst_n.value = 1
    await Timer(5, units="ns")


async def check_operation(dut, opcode, a, b):
    # Drive inputs
    dut.clk.value = 0
    dut.req_valid.value = 1
    dut.req_opcode.value = opcode
    dut.req_op1.value = a & 0xFFFF
    dut.req_op2.value = b & 0xFFFF

    await Timer(5, units="ns")

    # Rising clock edge
    dut.clk.value = 1

    await Timer(5, units="ns")

    # Check response
    assert int(dut.resp_done.value) == 1

    actual = int(dut.resp_result.value)
    expected = alu_ref(opcode, a, b)

    assert actual == expected, (
        f"Opcode={opcode:03b}, A={a}, B={b}, "
        f"Expected=0x{expected:04X}, "
        f"Actual=0x{actual:04X}"
    )


@cocotb.test()
async def test_basic_add(dut):
    await reset(dut)
    await check_operation(dut, ALU_ADD, 10, 20)


@cocotb.test()
async def test_positive_overflow(dut):
    await reset(dut)
    await check_operation(dut, ALU_ADD, 32767, 1)


@cocotb.test()
async def test_equality(dut):
    await reset(dut)
    await check_operation(dut, ALU_EQ, 5, 5)


@cocotb.test()
async def test_ready(dut):
    await reset(dut)
    assert int(dut.req_ready.value) == 1