SIM ?= verilator
TOPLEVEL_LANG ?= verilog
SRC_DIR := $(abspath ../../src)
# main currently has a stub. Supply the reviewed raw-core implementation.
MULTIPLIER_RTL ?= $(SRC_DIR)/exu/functional_units/multiplier.sv
VERILOG_SOURCES = $(SRC_DIR)/tinytracer_pkg.sv $(SRC_DIR)/tinytracer_if.sv
VERILOG_SOURCES += $(MULTIPLIER_RTL) $(CURDIR)/tb_multiplier.sv
TOPLEVEL = tb_multiplier
MODULE = test_multiplier
SIM_BUILD = sim_build
EXTRA_ARGS += --timing --trace -Wno-fatal
include $(shell cocotb-config --makefiles)/Makefile.sim
