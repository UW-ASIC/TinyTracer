# pixel_tx tests

cocotb + Verilator unit tests for the `pixel_tx` module (TinyTracer). Verifies
the block that takes a pixel colour from the Accumulator and frames it out to
the UART as `PIXEL_START, R, G, B`.

## Scope

the flat-port wrapper `pixel_tx_tb.sv` exposes the `colour_if` / `stream_if`
ports as plain top-level signals, so cocotb drives the pixel input
(`pixel_valid` / `pixel_colour`) and collects the byte output
(`tx_valid` / `tx_data` / `tx_ready`) directly, no hierarchical access needed.

a pixel goes out as `PIXEL_START` (0x00), then R, G, B, with a `DLE` (0x03) in
front of any colour byte equal to `0x00` or `0x03`. `0x01` is **not** escaped in
this direction. A reference encoder (`encode_pixel`) mirrors this framing and is
used to check the randomized tests; the hand-written tests keep their expected
bytes inline as an independent cross-check.

## Tests

| Test | What it checks |
|------|----------------|
| `test_escapes`               | colour bytes 0x00/0x03 get a DLE prefix; start byte and others go raw |
| `test_01_and_ff_not_escaped` | 0x01 and 0xFF pass through raw (TX escapes only 0x00/0x03) |
| `test_b2b`                   | two pixels back-to-back both frame correctly |
| `test_idle`                  | no pixel offered -> no bytes emitted (tx stays quiet) |
| `test_backpressure`          | random `tx_ready`: no byte dropped, doubled, or reordered |
| `test_backpressure_random`   | 200 random colours under random `tx_ready`, checked against the reference encoder |
| `test_random_ref`            | 200 random colours streamed back-to-back, checked against the reference encoder |
| `test_reset_midframe`        | reset partway through a pixel; module recovers and the next pixel sends cleanly |

All verified non-vacuous: breaking the reference encoder turns them 
red while the hand-written tests stay green, confirming the two are
independent.

## Running

Activate the cocotb venv, then from this directory:

    source ~/.venvs/tt/bin/activate   # once per terminal
    make -B