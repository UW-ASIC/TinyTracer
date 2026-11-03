# Tests the unsigned array core in UW-ASIC/TinyTracer PR #14.
# From this folder: make MULTIPLIER_RTL=/tmp/tinytracer-array-multiplier.sv
# Supply the PR RTL separately; the current main-branch RTL is a stub.

SIM ?= verilator
TOPLEVEL_LANG ?= verilog

SRC_DIR := $(abspath ../../src)
MULTIPLIER_RTL ?= $(SRC_DIR)/exu/functional_units/multiplier.sv

VERILOG_SOURCES = $(SRC_DIR)/tinytracer_pkg.sv
VERILOG_SOURCES += $(SRC_DIR)/tinytracer_if.sv
VERILOG_SOURCES += $(MULTIPLIER_RTL)
VERILOG_SOURCES += $(CURDIR)/tb_multiplier.sv

TOPLEVEL = tb_multiplier
MODULE = test_multiplier
SIM_BUILD = sim_build

EXTRA_ARGS += --timing --trace -Wno-fatal

include $(shell cocotb-config --makefiles)/Makefile.sim