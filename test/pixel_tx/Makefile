# Makefile for the pixel_tx tests
# Runs the cocotb tests (test_pixel_tx.py) against src/io/pixel_tx.sv through
# the flat-port wrapper pixel_tx_tb.sv (cocotb can't drive interface ports).
# Run with: make
# The Makefile in test/ runs the top-level tests in test.py.

SIM ?= verilator
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../../src

# tinytracer_pkg.sv and tinytracer_if.sv must come first: pixel_tx uses them.
VERILOG_SOURCES = $(SRC_DIR)/tinytracer_pkg.sv $(SRC_DIR)/tinytracer_if.sv \
                  $(SRC_DIR)/io/pixel_tx.sv $(PWD)/pixel_tx_tb.sv
TOPLEVEL = pixel_tx_tb
MODULE = test_pixel_tx
SIM_BUILD = sim_build

ifeq ($(SIM),verilator)
# Same flags as the main Makefile: the tests use timing and tracing
EXTRA_ARGS += --timing --trace -Wno-fatal --timescale 1ns/1ps
endif

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
