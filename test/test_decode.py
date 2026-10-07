import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer


@cocotb.test()
async def test_rom_functionality(dut):
    dut._log.info("Testing rom functionality")
    decode = dut.user_project.u_exu.u_decode

    decode.curr_addr.value = 0
    await Timer(1, units="ns")

    assert decode.micro_op_word == 0x0030 and decode.barrier == 0
