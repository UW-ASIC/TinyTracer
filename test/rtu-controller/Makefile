#Makefile for the RTU controller tests
#Runs test_rtu_controller.py on rtu.sv, using our test wrapper tb_rtu_controller.sv
#To run: make

SIM ?= verilator
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../../src

#We don't compile the real ray generator, intersection unit or shader core files
#tb_rtu_controller.sv has fake versions of them with the same names
VERILOG_SOURCES = $(SRC_DIR)/tinytracer_pkg.sv \
                  $(SRC_DIR)/tinytracer_if.sv \
                  $(SRC_DIR)/rtu/rtu.sv \
                  $(PWD)/tb_rtu_controller.sv
TOPLEVEL = tb_rtu_controller
MODULE = test_rtu_controller
SIM_BUILD = sim_build

ifeq ($(SIM),verilator)
#--public-flat-rw lets the python test read and write signals inside the rtu
EXTRA_ARGS += --timing --trace -Wno-fatal --public-flat-rw --timescale 1ns/1ps
endif

include $(shell cocotb-config --makefiles)/Makefile.sim