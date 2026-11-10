import os
from pathlib import Path
from cocotb.runner import get_runner

# CLI command: python runner.py
# Prerequisites - iverilog installed and in PATH, Python with cocotb==v1.9.2

TEST_DIR = Path(__file__).resolve().parent
SRC_DIR = TEST_DIR.parent.parent / "src"
BUILD_DIR = TEST_DIR / "sim_build"

def run_tests() -> None:
    sim = os.getenv("SIM", "icarus")

    runner = get_runner(sim)

    runner.build(
        verilog_sources=[SRC_DIR / "rtu" / "shader_core.sv", TEST_DIR / "tb_shader_core.sv"],
        hdl_toplevel="tb_shader_core",
        build_args=[],
        build_dir=BUILD_DIR,
        timescale=("1ns", "1ps"),
        waves=True,
        always=True,
    )

    runner.test(
        hdl_toplevel="tb_shader_core",
        test_module="test_shader_core",
        testcase=os.getenv("TESTCASE"),
        build_dir=BUILD_DIR,
        waves=True,
    )

if __name__ == "__main__":
    run_tests()
