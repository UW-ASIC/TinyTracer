# io parser unit tests (cocotb + Verilator)
#
# lives in test/io/. compiles only the sources the io parser needs, with a
# dedicated wrapper (tb_io.sv) that exposes io's render/sram interfaces. 
# this is separate from the repo's top-level test (test/tb.v + test/test.py)
#
# to run: source cocotb venv, then `make -B` from this directory.

SIM ?= verilator
TOPLEVEL_LANG ?= verilog

# test/io/ -> repo src is two levels up
SRC_DIR = $(PWD)/../../src

# tinytracer_pkg.sv and tinytracer_if.sv must stay first: everything uses them.
VERILOG_SOURCES += $(SRC_DIR)/tinytracer_pkg.sv
VERILOG_SOURCES += $(SRC_DIR)/tinytracer_if.sv
VERILOG_SOURCES += $(SRC_DIR)/io/clkdiv.sv
VERILOG_SOURCES += $(SRC_DIR)/io/uart.sv
VERILOG_SOURCES += $(SRC_DIR)/io/pixel_tx.sv
VERILOG_SOURCES += $(SRC_DIR)/io/io.sv
VERILOG_SOURCES += $(PWD)/tb_io.sv

TOPLEVEL = tb_io
MODULE   = test_io

# Match the repo's Verilator flags; -Wno-fatal keeps lint warnings from
# unfinished modules from aborting the build.
EXTRA_ARGS   += --timing --trace -Wno-fatal
COMPILE_ARGS += -I$(SRC_DIR)

include $(shell cocotb-config --makefiles)/Makefile.sim
