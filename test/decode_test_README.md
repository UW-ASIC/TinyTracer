# Decoder Tests

The decoder suite runs through `test_decode.py`, which imports the four test modules below so the existing `make DECODER_TEST=yes` command remains unchanged. A single test can still be selected with `make DECODER_TEST=yes TESTCASE=<test_name>`.

## 1. State Invariant Tests

- `test_curr_addr_stable_without_micro_accept`: Verifies that `curr_addr` does not change across clocks when no micro request is accepted.
- `test_no_macro_accept_while_busy`: Verifies that DISPATCH deasserts macro ready and cannot accept another macro operation.
- `test_inflight_increments_on_issue`: Verifies that accepting one micro request increments the inflight counter on the next rising edge.
- `test_inflight_decrements_on_completion`: Verifies that one micro completion decrements the inflight counter.
- `test_inflight_unchanged_on_issue_and_completion`: Verifies that simultaneous issue and completion cancel, leaving inflight unchanged.
- `test_writeback_stable_under_backpressure`: Verifies that WRITEBACK and `macro_resp_valid` remain asserted until the response receiver is ready.
- `test_vector_not_complete_with_inflight_ops`: Verifies that reaching the vector end address cannot complete the macro while work remains inflight.
- `test_barrier_stalls_until_inflight_zero`: Naturally reaches a DOT barrier and verifies that dispatch resumes only after all earlier micro operations complete.
- `test_micro_backpressure_stalls_and_resumes`: Verifies that micro backpressure preserves the pending ROM request, address, inflight count, and DISPATCH state until ready returns.
- `test_rf_load_pulses_on_macro_accept`: Verifies that `rf_load` asserts only during macro acceptance and does not repeat while the decoder is busy.

## 2. FSM Tests

- `test_reset_to_decode`: Verifies that reset places the FSM in DECODE.
- `test_reset_during_dispatch_with_inflight_ops`: Issues vector work, resets with one operation inflight, and verifies that all active control state is cleared.
- `test_reset_while_stalled_at_barrier`: Reaches a DOT barrier with outstanding work, resets there, and verifies that the abandoned operation does not restart.
- `test_reset_during_writeback`: Resets while a macro response is pending and verifies that the response is discarded.
- `test_scalar_macro_waits_for_micro_ready`: **THIS CURRENTLY FAILS**, demonstrating that the RTL accepts a scalar macro while its direct micro request is backpressured, potentially losing the request.
- `test_consecutive_vector_then_scalar`: Completes VADD followed by scalar SUB and verifies that vector state does not interfere with scalar completion.
- `test_consecutive_scalar_then_vector`: Completes scalar MUL followed by VSUB and verifies that scalar state does not interfere with vector dispatch or completion.
- `test_decode_to_dispatch`: Verifies that accepting a valid macro operation moves the FSM from DECODE to DISPATCH.
- `test_dispatch_stays_dispatch`: Verifies that unfinished micro work keeps the FSM in DISPATCH.
- `test_dispatch_to_writeback`: Verifies that completed vector work moves the FSM from DISPATCH to WRITEBACK.
- `test_writeback_stays_writeback`: Verifies that macro response backpressure keeps the FSM in WRITEBACK.
- `test_writeback_to_decode`: Verifies that accepting the macro response returns the FSM from WRITEBACK to DECODE.

## 3. Instruction Decode and ROM Tests

- `test_rom_functionality`: Verifies that ROM address zero returns the first VADD micro operation with no barrier.
- `test_scalar_macro_conversion`: Verifies the direct micro opcode and scalar operand fields for every defined scalar macro opcode.
- `test_vector_rom_ranges`: Verifies that every vector macro opcode loads its correct inclusive start and exclusive end addresses.
- `test_vector_format_capture_and_retention`: Verifies both format values are captured on vector acceptance and retained while the macro input changes during dispatch.
- `test_rom_contents`: Verifies every defined ROM address against its expected 13-bit micro instruction and barrier bit.
- `test_rom_default_entry`: Verifies that an unused ROM address returns a zero micro instruction with no barrier.

## 4. Big Tests

- `test_decode_scalar_then_vector`: Runs scalar operations before vector operations to verify the transition between dispatch modes.
- `test_decode_vector_then_scalar`: Runs vector operations before scalar operations to verify that vector state does not leak into later direct requests.
- `test_decode_alternating_formats`: Alternates both supported formats while varying request gaps, readiness, and completion latency.
- `test_decode_format_zero_stream`: Holds format zero across an extended mixed-operation stream.
- `test_decode_format_one_stream`: Holds format one across an extended mixed-operation stream.
- `test_decode_scalar_bursts`: Sends scalar-heavy bursts separated by vector work.
- `test_decode_vector_bursts`: Sends vector-heavy bursts separated by scalar work.
- `test_decode_geometry_heavy`: Emphasizes longer geometry-related vector macro sequences while retaining full opcode coverage.
- `test_decode_arithmetic_heavy`: Emphasizes scalar and short vector arithmetic sequences while retaining full opcode coverage.
- `test_decode_continuous_input`: Removes idle gaps and accepts macro responses immediately to model continuous traffic.
- `test_decode_gapped_input`: Inserts regular idle gaps and response stalls between transactions.
- `test_decode_micro_backpressure`: Applies sustained micro-request backpressure during vector dispatch.
- `test_decode_bursty_micro_ready`: Alternates bursts of micro-request readiness and backpressure.
- `test_decode_short_micro_latency`: Completes accepted micro-operations with the minimum modeled latency.
- `test_decode_long_micro_latency`: Keeps multiple micro-operations inflight using longer completion delays.
- `test_decode_response_backpressure`: Holds completed macro responses in WRITEBACK for several cycles.
- `test_decode_balanced_pipeline`: Mixes operation types and timing conditions to exercise ordinary pipeline overlap.
- `test_decode_barrier_pressure`: Emphasizes vector sequences containing barriers and delayed earlier completions.
- `test_decode_mixed_render_math`: Interleaves geometry, arithmetic, scalar, and vector work to resemble render-related decoder traffic.
- `test_decode_full_stress`: Combines reversed opcode ordering, request gaps, micro backpressure, long completions, and response stalls.
