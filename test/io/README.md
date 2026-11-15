# io parser tests

cocotb + Verilator unit tests for the `io` message parser (TinyTracer).
Verifies the parser that turns the UART byte stream into RENDER strobes and
SRAM writes.

## Scope

These tests drive the parser's input stream (`rx_bytes`) **directly** instead of
feeding serial bits through the UART. `uart_rx` is held idle (`1`) so the live 
UART stays parked and doesn't inject competing bytes.

cocotb reaches the internal stream hierarchically (`dut.dut_io.rx_bytes.*`).
The wrapper `tb_io.sv` breaks out the render and SRAM interface signals as
top-level wires, and exposes `sram.req_ready` as a drivable signal
(`sram_req_ready_drv`, defaults high) so the backpressure test can hold it low.

## Tests

| Test | What it checks |
|------|----------------|
| `test_render`          | RENDER decodes img_w/img_h and pulses `render` (one cycle) |
| `test_object`          | OBJECT issues one SRAM write (addr, data, wen=1) |
| `test_dle`             | DLE (0x03) escape: an escaped 0x03 is delivered as data |
| `test_dle_multiple`    | two escaped 0x03 bytes in one message stay aligned |
| `test_invalid_start`   | a junk first byte is ignored; parser recovers on the next message |
| `test_masked_bits`     | only the intended source bits feed each field (width nibble, addr bit 0) |
| `test_render_extremes` | dim min (0x000) and max (0xFFF) round-trip exactly |
| `test_object_extremes` | data/addr min (0x0000/0x000) and max (0xFFFF/0x1FF) round-trip |
| `test_b2b`             | back-to-back messages both parse (state resets between them) |
| `test_backpressure`    | a write is held while `sram.req_ready` is low, completes when raised |

All verified non-vacuous (each fails when its expected value or stimulus is
deliberately broken).

## Running

Activate the cocotb venv, then from this directory:

    source ~/.venvs/tt/bin/activate   # once per terminal
    make -B
