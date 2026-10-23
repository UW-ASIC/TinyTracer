# Makefile for the reg_file tests
# Runs the register file cocotb tests (test_reg_file.py) directly against
# src/exu/reg_file.sv, with reg_file as the toplevel. Run with: make
# The Makefile in test/ runs the top-level tests in test.py.

SIM ?= verilator
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../../src

# Load variant under test: multi (default, 2 words over 3 cycles) or single
# (all six words in one cycle). Use: make REG_FILE_LOAD=single
REG_FILE_LOAD ?= multi
export REG_FILE_LOAD

# tinytracer_pkg.sv must come first: reg_file uses it.
VERILOG_SOURCES = $(SRC_DIR)/tinytracer_pkg.sv $(SRC_DIR)/exu/reg_file.sv
TOPLEVEL = reg_file
MODULE = test_reg_file
SIM_BUILD = sim_build

ifeq ($(SIM),verilator)
# Same flags as the main Makefile: the tests use timing and tracing
EXTRA_ARGS += --timing --trace -Wno-fatal
endif

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
