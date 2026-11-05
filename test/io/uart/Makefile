# Makefile for the UART tests
# Runs the UART cocotb tests (test_uart.py) against src/io/uart.sv, through the
# tb_uart.sv wrapper that flattens the stream_if ports. Run with: make
# The Makefile in test/ runs the top-level tests in test.py.

SIM ?= verilator
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../../../src

# tinytracer_pkg.sv and tinytracer_if.sv must come first: uart.sv uses them.
VERILOG_SOURCES = $(SRC_DIR)/tinytracer_pkg.sv $(SRC_DIR)/tinytracer_if.sv $(SRC_DIR)/io/uart.sv $(PWD)/tb_uart.sv
TOPLEVEL = tb_uart
MODULE = test_uart
SIM_BUILD = sim_build

ifeq ($(SIM),verilator)
# Same flags as the main Makefile: the tests use timing and tracing
EXTRA_ARGS += --timing --trace -Wno-fatal
endif

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
