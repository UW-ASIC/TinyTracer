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
* Configures the output image width and height

__OBJECT Messages__:

| OBJ_START | OBJ_MESSAGE_LOW | OBJ_MESSAGE_HIGH | OBJ_ADDR_LOW | OBJ_ADDR_HIGH |
|:----:|:----:|:----:|:----:|:----:|
| 0x01 | Object message lower byte | Object message upper byte | Lower 8 bits of SRAM address | Upper 8 bits of SRAM address |

* Transmits individual primitives/bounding volumes to be written to SRAM

## Output Frames

__PIXEL Messages__

| PIXEL_START | RED | GREEN | BLUE |
|:----:|:----:|:----:|:----:|
| 0x00 | 0x00-0xFF  | 0x00-0xFF | 0x00-0xFF |

* Transmits a single pixel to the host device to display

## Data Link Escape
To be able to transmit data values equal to these message start flags, we utilize a specialized byte code, a data link escape (`DLE`) which is used to signify that the next byte is data, not a control message.
A DLE has a value of `0x03`.

An example of using the DLE byte would be to transmit the value `0x03`, we would have to transmit 2 bytes: `0x03`(DLE) followed by `0x03` (0x03 as data).
