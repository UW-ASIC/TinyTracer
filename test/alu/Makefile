SIM ?= verilator
TOPLEVEL_LANG = verilog

SRC_DIR = $(abspath ../../src)

VERILOG_SOURCES = \
    $(SRC_DIR)/tinytracer_pkg.sv \
    $(SRC_DIR)/tinytracer_if.sv \
    $(SRC_DIR)/exu/functional_units/alu.sv \
    $(CURDIR)/alu_tb_top.sv

TOPLEVEL = alu_tb_top
MODULE = test_alu

export PYTHONPATH := $(abspath ..):$(PYTHONPATH)

COMPILE_ARGS += -Wno-fatal

include $(shell cocotb-config --makefiles)/Makefile.sim