# UART Frame Encoding

**Input:** Custom Commands

**Output:** Bitmap (format TBD)

Dataflow: PC → Tiny Tracer → PC

1) PC sends object file to Tiny Tracer

2) Tiny Tracer processes pixels from left to right, top to bottom, one at a time

3) For each processed pixel (i.e. RGB values are computed), the RGB values are sent over UART back to the PC

4) As PC receives RGB values, a Python script will pack the last 3 bytes received into a single pixel

5) Once a pixel's color is updated on display, (x,y) coordinates will change accordingly to update the next pixel

5) Python script will refresh display as new pixels come in

6) Once all the pixels come in, Python script will save image as a file (format TBD)

Note: will need to do some research on what Python libraries can reliably refresh displays one pixel at a time

## Frame Formats

### Input Frames

__RENDER Messages__:

* Renders the environment stored in the environment memory (i.e., runs the ray-tracing algorithm)

| RENDER_START |
|----|
| 0x00 |

__OBJECT Messages__:

* Transmit individual primitives/bounding volumes over UART to chip
  * 80 bits for bounding volumes


  * 176 bits for triangles
  * 96 bits for spheres
* Begin loading object data into SRAM starting from address OBJ_DATA_START
  * Python script will do the following:
    * Break down object data into individual SRAM write messages:
      * For bounding volumes, 5 messages are sent (16 bits \* 5 writes)


      * For triangles, 11 messages are sent (16 bits \* 11 writes)
      * For spheres, 6 messages are sent (16 bits \* 6 writes)
    * Sort shapes into BVH before transmitting to chip
* This message can also initialize the LUT in SRAM

| OBJ_START | OBJ_MESSAGE_LOW | OBJ_MESSAGE_HIGH | OBJ_ADDR_LOW | OBJ_ADDR_HIGH |
|----|----|----|----|----|
| 0x01 | Object message lower byte | Object message upper byte | Lower 8 bits of SRAM address | Upper 8 bits of SRAM address |

### Output Frames

__PIXEL Messages__

* Transmits a single pixel to display

| PIXEL_START | RED | GREEN | BLUE |
|----|----|----|----|
| 0x00 | 0x00-0xFF  | 0x00-0xFF | 0x00-0xFF |

## Components

### UART to USB PMOD

<https://digilent.com/shop/pmod-usbuart-usb-to-uart-interface/?srsltid=AfmBOoq31kt_PhRTmbX2ydW9kKjP8GyQcVRyRFMMuBCKn3S-9090fFwO>