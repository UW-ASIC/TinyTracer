# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

# Keep the existing cocotb MODULE=test_decode entry point while organizing
# decoder coverage by category.
from test_decode_invariants import *
from test_decode_fsm import *
from test_decode_instruction_rom import *
from test_decode_big import *
