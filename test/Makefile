# Makefile
# See https://docs.cocotb.org/en/stable/quickstart.html for more info

# defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../src
PROJECT_SOURCES += accumulator.v
PROJECT_SOURCES += alu.v
PROJECT_SOURCES += cordic.v
PROJECT_SOURCES += decode.v
PROJECT_SOURCES += functional_units.v
PROJECT_SOURCES += intersection_unit.v
PROJECT_SOURCES += io.v
PROJECT_SOURCES += multiplier.v
PROJECT_SOURCES += ray_generator.v
PROJECT_SOURCES += ray_tracing_unit.v
PROJECT_SOURCES += reg_file.v
PROJECT_SOURCES += shader_core.v
PROJECT_SOURCES += sram_control.v
PROJECT_SOURCES += sram_sim.v
PROJECT_SOURCES += tinytracer_defs.vh
PROJECT_SOURCES += tt_um_tinytracer.v
PROJECT_SOURCES += uart.v
PROJECT_SOURCES += xorshift_rng.v

ifneq ($(GATES),yes)

# RTL simulation:
SIM_BUILD				= sim_build/rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))

else

# Gate level simulation:
SIM_BUILD				= sim_build/gl
COMPILE_ARGS    += -DGL_TEST
COMPILE_ARGS    += -DFUNCTIONAL
COMPILE_ARGS    += -DUSE_POWER_PINS
COMPILE_ARGS    += -DSIM
COMPILE_ARGS    += -DUNIT_DELAY=\#1
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v
VERILOG_SOURCES += $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v

# this gets copied in by the GDS action workflow
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v

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
