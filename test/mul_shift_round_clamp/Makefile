# Makefile for the fixed-point multiply tests
# Runs test_mul_shift_round_clamp.py against mul_shift_round_clamp (Booth product, shift, round,
# clamp) through tb.v. Run with: make
# The multiplier.sv wrapper around it uses fu_if, which Icarus cannot parse,
# so it is compiled by the top-level tests in test/ instead.

SIM ?= icarus
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(CURDIR)/../../src

FU_DIR = $(SRC_DIR)/exu/functional_units

VERILOG_SOURCES = $(FU_DIR)/booth_row.sv
VERILOG_SOURCES += $(FU_DIR)/csa.sv
VERILOG_SOURCES += $(FU_DIR)/booth_mul16.sv
VERILOG_SOURCES += $(FU_DIR)/mul_shift_round_clamp.sv
VERILOG_SOURCES += $(CURDIR)/tb.v
TOPLEVEL = tb
MODULE = test_mul_shift_round_clamp
SIM_BUILD = sim_build

ifeq ($(SIM),verilator)
# Same flags as the main Makefile: tb.v uses delays and $dumpvars
EXTRA_ARGS += --timing --trace -Wno-fatal
endif

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
