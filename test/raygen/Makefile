SIM ?= verilator
TOPLEVEL_LANG ?= verilog

SRC_DIR := $(abspath $(CURDIR)/../../src)

VERILOG_SOURCES += $(SRC_DIR)/tinytracer_pkg.sv
VERILOG_SOURCES += $(SRC_DIR)/tinytracer_if.sv
VERILOG_SOURCES += $(SRC_DIR)/rtu/ray_gen/rng.sv
VERILOG_SOURCES += $(SRC_DIR)/rtu/ray_gen/ray_generator.sv
VERILOG_SOURCES += $(CURDIR)/tb_raygen.sv

COMPILE_ARGS += -I$(SRC_DIR)
EXTRA_ARGS += --timing --trace -Wno-fatal
SIM_BUILD := $(CURDIR)/sim_build

TOPLEVEL = tb_raygen
MODULE = test_raygen
# Compatibility with cocotb 2.x naming
export COCOTB_TOPLEVEL = tb_raygen
export COCOTB_TEST_MODULES = test_raygen

# The ray-generator-rtl branch has test/reference_models/raygen.py.
export PYTHONPATH := $(abspath $(CURDIR)/..):$(CURDIR):$(PYTHONPATH)

ifeq ($(MAKECMDGOALS),clean)
.PHONY: clean
clean:
	rm -rf sim_build results.xml raygen.vcd raygen.fst
else
include $(shell cocotb-config --makefiles)/Makefile.sim
endif
