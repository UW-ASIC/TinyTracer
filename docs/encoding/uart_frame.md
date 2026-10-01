---
description: "Format of the UART frames exchanged between the host device and TinyTracer to load scenes and stream rendered pixels."
---

# UART Frame Encoding

## Input Frames

__RENDER Messages__:

| RENDER_START | IMG_W_LOW | IMG_W_HIGH | IMG_H_LOW | IMG_H_HIGH |
|:----:|:----:|:----:|:----:|:----:|
| 0x00 | Image width lower byte | Image width upper byte | Image height lower byte | Image height upper byte |

* Renders the scene stored in SRAM by pulsing the RTU's `render` signal for one cycle
* Configures the output image width and height. The I/O Unit keeps the low 12 bits of each (`DIM_WIDTH`); the upper 4 bits of each high byte are unused. The image must be square, with a width that is a power of 2 and at most 512 (the RTU's pixel counters are 9 bits)
* The samples per pixel, camera, and sky and ground colours come from the scene header in SRAM, not from this message (see [Scene Encoding](scene.md))

__OBJECT Messages__:

| OBJ_START | OBJ_MESSAGE_LOW | OBJ_MESSAGE_HIGH | OBJ_ADDR_LOW | OBJ_ADDR_HIGH |
|:----:|:----:|:----:|:----:|:----:|
| 0x01 | Object message lower byte | Object message upper byte | Lower 8 bits of SRAM address | Upper 8 bits of SRAM address |

* Writes one 16-bit word of the scene (header, bounding volume, or primitive) to SRAM (see [Scene Encoding](scene.md)). One message is sent per word
* The SRAM address is 9 bits: bit 0 of `OBJ_ADDR_HIGH` is address bit 8, and the other bits of `OBJ_ADDR_HIGH` are 0

## Output Frames

__PIXEL Messages__

| PIXEL_START | RED | GREEN | BLUE |
|:----:|:----:|:----:|:----:|
| 0x00 | 0x00-0xFF  | 0x00-0xFF | 0x00-0xFF |

* Transmits a single pixel to the host device to display
* Pixels are sent row by row, one per message, as the RTU finishes them. The I/O Unit sends one pixel while the RTU renders the next

## Data Link Escape
To be able to transmit data values equal to these message start flags, we utilize a specialized byte code, a data link escape (`DLE`) which is used to signify that the next byte is data, not a control message.
A DLE has a value of `0x03`.

An example of using the DLE byte would be to transmit the value `0x03`, we would have to transmit 2 bytes: `0x03`(DLE) followed by `0x03` (0x03 as data).

The data bytes that must be sent after a DLE are:

| Direction | Escaped data bytes |
|----|----|
| Host to TinyTracer (RENDER, OBJECT) | `0x00` (`RENDER_START`), `0x01` (`OBJ_START`), `0x03` (`DLE`) |
| TinyTracer to host (PIXEL) | `0x00` (`PIXEL_START`), `0x03` (`DLE`) |

Every byte, including a DLE, is sent as a 10-bit UART frame (start bit, 8 data bits, stop bit), so a PIXEL message takes 40 bits plus 10 bits per escaped colour byte.
