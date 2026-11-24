# Makefile for the clkdiv tests
# Runs the clock divider cocotb tests (test_clkdiv.py) directly against
# src/io/clkdiv.sv, with clkdiv as the toplevel. Run with: make
# The Makefile in test/ runs the top-level tests in test.py.

SIM ?= verilator
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../../src

# The timescale file must come first: Icarus has no default timescale, and cocotb's
# 40 ns clock is not representable at the default 1s precision.
VERILOG_SOURCES = $(PWD)/clkdiv_timescale.v $(SRC_DIR)/io/clkdiv.sv
TOPLEVEL = clkdiv
MODULE = test_clkdiv
SIM_BUILD = sim_build

# reference_models lives in test/
export PYTHONPATH := $(PWD)/..:$(PYTHONPATH)

ifeq ($(SIM),verilator)
# Same flags as the main Makefile: the tests use timing and tracing
EXTRA_ARGS += --timing --trace -Wno-fatal
endif

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
