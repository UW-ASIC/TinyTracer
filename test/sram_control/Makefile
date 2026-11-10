SIM ?= verilator
TOPLEVEL_LANG = verilog
SRC_DIR = $(PWD)/../../src

VERILOG_SOURCES += $(SRC_DIR)/tinytracer_pkg.sv
VERILOG_SOURCES += $(SRC_DIR)/tinytracer_if.sv
VERILOG_SOURCES += $(SRC_DIR)/sram_control.sv
VERILOG_SOURCES += $(PWD)/tb_sram_control.sv

EXTRA_ARGS   += --timing --trace -Wno-fatal
COMPILE_ARGS += -I$(SRC_DIR)

TOPLEVEL = tb_sram_control
MODULE = test_sram_control

include $(shell cocotb-config --makefiles)/Makefile.sim