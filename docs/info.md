<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

TinyTracer is a small ray-tracing graphics chip. A host device, such as a laptop, sends a 3D scene over a UART: a header with the camera and the sky and ground colours, up to 16 bounding volumes, and a list of spheres and triangles with matte, mirror, glass, or glowing materials. The chip stores the scene in a 512-word, 16-bit on-chip SRAM.

When the host sends a RENDER message, the chip renders the image one pixel at a time. For each pixel it traces 1 to 32 rays (samples) through slightly different points of the pixel, follows each ray through up to 8 bounces off the scene's surfaces and a checkered ground plane, and averages the samples. It sends each finished pixel back over the UART while it renders the next one.

Inside, a Ray Tracing Unit runs the ray-tracing algorithm and sends vector and scalar operations (macro-ops) to an Execution Unit. The Execution Unit splits them into micro-ops for an ALU, a multiplier, and a CORDIC unit. All arithmetic is 16-bit fixed point: Q9.7 for positions and distances, and Q2.14 for directions.

The full design documentation is at https://uw-asic.github.io/TinyTracer/.

## How to test

1. Connect a 3.3 V USB-to-UART adapter: the adapter's TX to `ui_in[3]` (`uart_rx`) and its RX to `uo_out[4]` (`uart_tx`). Frames have 8 data bits, no parity, and 1 stop bit.
2. The baud rate comes from an on-chip fractional clock divider. Its configuration inputs are not assigned to pins yet.
3. Send the scene one 16-bit word at a time with OBJECT messages: `0x01`, the word's low byte, its high byte, the address's low byte, and its high byte.
4. Send a RENDER message to start: `0x00`, then the image width and height, each as a low byte and a high byte. The image must be square, with a width that is a power of 2 and at most 512.
5. Read back one PIXEL message per pixel, row by row: `0x00`, then the red, green, and blue bytes.
6. In both directions, a data byte that equals a message start byte or `0x03` is sent after a `0x03` escape byte.

The software model in `sim/tinytracer_sim.cpp` builds the SRAM image from a scene file such as `sim/scene_demo.txt` and renders it with the same arithmetic as the chip, so its output can be compared with the chip's.

## External hardware

A 3.3 V USB-to-UART adapter.
