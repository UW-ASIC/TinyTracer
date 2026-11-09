# Makefile for the radix-4 Booth multiplier tests
# Runs test_booth_mul16.py against the multiplier through its Tiny Tapeout-style
# wrapper (tt_um_booth_mul16) and tb.v. Run with: make
# The Makefile in test/ runs the top-level tests in test.py.

# booth_mul16 is plain Verilog-2005, so Icarus can run it, unlike the top level.
SIM ?= icarus
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(CURDIR)/../../src

FU_DIR = $(SRC_DIR)/exu/functional_units

VERILOG_SOURCES = $(FU_DIR)/booth_row.sv
VERILOG_SOURCES += $(FU_DIR)/csa.sv
VERILOG_SOURCES += $(FU_DIR)/booth_mul16.sv
VERILOG_SOURCES += $(FU_DIR)/tt_um_booth_mul16.sv
VERILOG_SOURCES += $(CURDIR)/tb.v
TOPLEVEL = tb
MODULE = test_booth_mul16
SIM_BUILD = sim_build

ifeq ($(SIM),verilator)
# Same flags as the main Makefile: tb.v uses delays and $dumpvars
EXTRA_ARGS += --timing --trace -Wno-fatal
endif

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
