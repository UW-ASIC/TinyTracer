# Makefile for the FU Control tests
# Runs fu_tb.py against fu_control with the register file and functional
# units, with fu_tb_top as the toplevel. Run with: make

SIM ?= verilator
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../../src
FU_DIR = $(SRC_DIR)/exu/functional_units

# tinytracer_pkg.sv and tinytracer_if.sv must stay first: every other file uses them.
VERILOG_SOURCES = $(SRC_DIR)/tinytracer_pkg.sv $(SRC_DIR)/tinytracer_if.sv
VERILOG_SOURCES += $(SRC_DIR)/exu/reg_file.sv
VERILOG_SOURCES += $(FU_DIR)/fu_control.sv $(FU_DIR)/alu.sv
VERILOG_SOURCES += $(FU_DIR)/multiplier.sv $(FU_DIR)/cordic.sv
VERILOG_SOURCES += $(PWD)/fu_tb_top.sv
TOPLEVEL = fu_tb_top
MODULE = fu_tb
SIM_BUILD ?= sim_build

ifeq ($(SIM),verilator)
EXTRA_ARGS += --timing --trace -Wno-fatal
endif

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
