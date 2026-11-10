import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

# --- CONFIGURATION ---
CLK_PERIOD_NS = 40  # 25MHz

# TODO: Maybe generate list of state names and values from RTL somehow
STATE_IDLE = 0

OTHER_INPUTS = {
    "new_sample": 1,
    "hit": 1,
    "hit_ground": 1,
    "hit_addr": 9,
    "last_bounce": 1,
    "ray_origin": 48,
    "ray_dir": 48,
    "sky_horizon": 24,
    "sky_top": 24,
    "ground_a": 24,
    "ground_b": 24,
    "sram_data": 16,
    "sram_valid": 1,
    "req_ready": 1,
    "resp_valid": 1,
    "resp_result": 48,
}

# --- HELPERS ---
def check_idle(dut, when):
    """Checks that state is STATE_IDLE"""
    state = dut.u1.state_r.value
    assert int(state) == STATE_IDLE, f"state_r is {int(state)}, not STATE_IDLE {when}"

# --- TEST CASES ---
@cocotb.test()
async def test_idle_without_start(dut):
    """With start=0, SC should stay in STATE_IDLE in all situations."""
    test_cycles = 1000

    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, units="ns").start())

    dut.start.value = 0
    for name in OTHER_INPUTS:
        getattr(dut, name).value = 0

    # Reset on
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)

    # Check state
    await FallingEdge(dut.clk)
    check_idle(dut, "after reset")

    # Reset off
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1

    # For many cycles
    for cycle in range(test_cycles):
        # Change other inputs on falling edges
        for name, width in OTHER_INPUTS.items():
            getattr(dut, name).value = random.getrandbits(width)
        await RisingEdge(dut.clk)

        # Check state after rising edges
        check_idle(dut, f"after cycle {cycle}")
        await FallingEdge(dut.clk)
    
    dut._log.info(f"state_r stayed STATE_IDLE for {test_cycles} cycles with start = 0")