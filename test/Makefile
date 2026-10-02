# Makefile
# See https://docs.cocotb.org/en/stable/quickstart.html for more info

# defaults
SIM ?= verilator
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../src
# tinytracer_pkg.sv and tinytracer_if.sv must stay first: every other file uses them.
PROJECT_SOURCES += tinytracer_pkg.sv
PROJECT_SOURCES += tinytracer_if.sv
PROJECT_SOURCES += tt_um_tinytracer.sv
PROJECT_SOURCES += accumulator.sv
PROJECT_SOURCES += sram_control.sv
PROJECT_SOURCES += scene_sram.sv
PROJECT_SOURCES += exu/exu.sv
PROJECT_SOURCES += exu/decode.sv
PROJECT_SOURCES += exu/reg_file.sv
PROJECT_SOURCES += exu/functional_units/alu.sv
PROJECT_SOURCES += exu/functional_units/cordic.sv
PROJECT_SOURCES += exu/functional_units/fu_control.sv
PROJECT_SOURCES += exu/functional_units/multiplier.sv
PROJECT_SOURCES += io/io.sv
PROJECT_SOURCES += io/uart.sv
PROJECT_SOURCES += io/clkdiv.sv
PROJECT_SOURCES += rtu/intersection_unit.sv
PROJECT_SOURCES += rtu/ray_gen/ray_generator.sv
PROJECT_SOURCES += rtu/ray_gen/rng.sv
PROJECT_SOURCES += rtu/rtu.sv
PROJECT_SOURCES += rtu/shader_core.sv

ifneq ($(GATES),yes)

# RTL simulation:
SIM_BUILD				= sim_build/rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))

else

# Gate level simulation: the flat netlist and the IHP sg13cmos5l cell models
# simulate with Icarus, which does not support the SystemVerilog interfaces used in RTL.
SIM             = icarus
SIM_BUILD				= sim_build/gl
COMPILE_ARGS    += -DGL_TEST
COMPILE_ARGS    += -DFUNCTIONAL
COMPILE_ARGS    += -DSIM
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_io/verilog/sg13cmos5l_io.v
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/verilog/sg13cmos5l_stdcell.v
# The scene SRAM macro: FUNCTIONAL selects its behavioural model
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_sram/verilog/RM_IHPSG13_1P_512x16_c2_bm_bist.v
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_sram/verilog/RM_IHPSG13_1P_core_behavioral_bm_bist.v

# this gets copied in by the GDS action workflow
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v

endif

ifeq ($(SIM),verilator)
# RTL simulation with Verilator: the testbench uses delays and $dumpvars, and
# lint warnings from unfinished modules must not abort the build.
EXTRA_ARGS      += --timing --trace -Wno-fatal
endif

# Allow sharing configuration between design and testbench via `include`:
COMPILE_ARGS 		+= -I$(SRC_DIR)

# Include the testbench sources:
VERILOG_SOURCES += $(PWD)/tb.v
TOPLEVEL = tb

# MODULE is the basename of the Python test file
MODULE = test

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
