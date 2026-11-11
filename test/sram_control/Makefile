SIM ?= verilator
TOPLEVEL_LANG = verilog
SRC_DIR = $(CURDIR)/../../src

VERILOG_SOURCES += $(SRC_DIR)/tinytracer_pkg.sv
VERILOG_SOURCES += $(SRC_DIR)/tinytracer_if.sv
VERILOG_SOURCES += $(SRC_DIR)/sram_control.sv
VERILOG_SOURCES += $(CURDIR)/tb_sram_control.sv

EXTRA_ARGS   += --timing --trace -Wno-fatal
COMPILE_ARGS += -I$(SRC_DIR)

# cocotb 1.x names
TOPLEVEL = tb_sram_control
MODULE   = test_sram_control
# cocotb 2.x names (harmless on 1.x)
COCOTB_TOPLEVEL = tb_sram_control
COCOTB_TEST_MODULES = test_sram_control

include $(shell cocotb-config --makefiles)/Makefile.sim