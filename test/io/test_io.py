import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge


# helper function to inject bytes into the parser input (rx_bytes)
async def send_byte(dut, value):
    """inject 1 byte to the parser input (rx_bytes)"""

    # rx_fire = rx_bytes.valid && rx_bytes.ready
    # we wait for ready, raise valid with data for 1 clk edge, then lower valid
    
    while True:
        await RisingEdge(dut.clk)                   # wait until parser is ready to accept a byte

        if int(dut.dut_io.rx_bytes.ready.value) == 1:
            break


    # present the byte with valid high
    # fires on next clk edge if both valid and ready are high
    dut.dut_io.rx_bytes.data.value = value
    dut.dut_io.rx_bytes.valid.value = 1
    await RisingEdge(dut.clk)                       # hold valid for 1 clk edge

    # drop valid, clear data, let the parser settle before next byte
    dut.dut_io.rx_bytes.data.value = 0
    dut.dut_io.rx_bytes.valid.value = 0
    await ClockCycles(dut.clk, 1)                   # wait a few cycles for things to settle


async def send_bytes(dut, values):
    """inject a list of bytes to the parser input (rx_bytes)"""

    for value in values:
        await send_byte(dut, value)


@cocotb.test()
async def test_render(dut):
    """render test, sends render command to parser, waits for render pulse, and checks w / h values"""
    dut._log.info("start render test")

    # setup (clock + reset)
    clock = Clock(dut.clk, 40, units="ns")          # starts clock (25MHz)
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.uart_rx.value = 1                           # we're not even using this, so keep idle at 1
    dut.clkdiv_ctl.value = 0                        # clkdiv not even used, so keep floating at 0
    dut.clkdiv_data.value = 0
    dut.dut_io.rx_bytes.valid.value = 0
    dut.dut_io.rx_bytes.data.value = 0
    await ClockCycles(dut.clk, 5)                   # hold reset low for 5 cycles
    dut.rst_n.value = 1                             # release reset
    await ClockCycles(dut.clk, 2)                   # wait 2 cycles for things to settle, then parser live

    dim = 0x123                                     # artbitrary test value
    dim_low = dim & 0xFF                            # grabs lower 8 bits -> 0x23
    dim_high = (dim >> 8) & 0xFF                    # shifts down, masks lower 8 bits -> 0x01


    # catches the one cycle render pulse (bgd monitoring)
    seen = {"pulsed": False, "w": None, "h": None}

    async def monitor_render():
        while True:                                 # infinite loop that checks if render_strobe is high on every clk edge 
            await RisingEdge(dut.clk)

            if int(dut.render_strobe.value) == 1:
                seen["pulsed"] = True
                seen["w"] = int(dut.render_img_w.value)                     # captures img_w value at moment of pulse
                seen["h"] = int(dut.render_img_h.value)                     # captures img_h value at moment of pulse

    cocotb.start_soon(monitor_render())

    await send_bytes(dut, [0x00, dim_low, dim_high, dim_low, dim_high])     # inject render msg, 4 payload bytes (RENDER_START, width low / high, height low / high)
    await ClockCycles(dut.clk, 5)                                           # wait a few cycles for things to settle

    # the check
    assert seen["pulsed"] == True, "render pulse not seen after render message"
    assert seen["w"] == dim, f"render width mismatch: expected {dim:#05x}, got {seen['w']:#05x}"    # #05x for formatting in output msg only, purely cosmetic
    assert seen["h"] == dim, f"render height mismatch: expected {dim:#05x}, got {seen['h']:#05x}"

    dut._log.info(f"render test passed: width=height={dim:#05x}")

@cocotb.test()
# basically same layout as render test, but for sram write command instead of render command
async def test_object(dut):
    """object test, sends 1 sram write command to parser with the right addr and data"""
    dut._log.info("start object test")

    # setup (clock + reset)
    clock = Clock(dut.clk, 40, units="ns")          # starts clock (25MHz)
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.uart_rx.value = 1                           # we're not even using this, so keep idle at 1
    dut.clkdiv_ctl.value = 0                        # clkdiv not even used, so keep floating at 0
    dut.clkdiv_data.value = 0
    dut.dut_io.rx_bytes.valid.value = 0
    dut.dut_io.rx_bytes.data.value = 0
    await ClockCycles(dut.clk, 5)                   # hold reset low for 5 cycles
    dut.rst_n.value = 1                             # release reset
    await ClockCycles(dut.clk, 2)                   # wait 2 cycles for things to settle, then parser live

    data = 0xABCD                                   # arbitrary test value (16 bits)
    addr = 0x123                                    # arbitrary test value (9 bits)
    data_low = data & 0xFF                          # grabs lower 8 bits -> 0xCD
    data_high = (data >> 8) & 0xFF                  # shifts down, masks lower 8 bits -> 0xAB
    addr_low = addr & 0xFF                          # grabs lower 8 bits -> 0x23
    addr_high = (addr >> 8) & 0xFF                  # shifts down, masks lower 8 bits

    # catches the sram write (bgd monitoring)
    seen = {"wrote": False, "addr": None, "data": None, "wen": None}

    async def monitor_sram():
        while True:                                # infinite loop that checks if sram_req_valid is high on every clk edge
            await RisingEdge(dut.clk)

            if int(dut.sram_req_valid.value) == 1 and not seen["wrote"]:
                seen["wrote"] = True
                seen["addr"] = int(dut.sram_req_waddr.value)                     # captures addr value at moment of write
                seen["data"] = int(dut.sram_req_wdata.value)                     # captures data value at moment of write
                seen["wen"] = int(dut.sram_req_wen.value)                        # captures wen (write enable) value at moment of write

    cocotb.start_soon(monitor_sram())

    await send_bytes(dut, [0x01, data_low, data_high, addr_low, addr_high])     # inject sram write msg, 4 payload bytes (SRAM_WRITE, data low / high, addr low / high)
    await ClockCycles(dut.clk, 5)                                               # wait a few cycles for things to settle

    # the check
    assert seen["wrote"] == True, "sram write not seen after object message"
    assert seen["addr"] == addr, f"waddr mismatch: expected {addr:#05x}, got {seen['addr']:#05x}"
    assert seen["data"] == data, f"wdata mismatch: expected {data:#06x}, got {seen['data']:#06x}"
    assert seen["wen"] == 1, f"wen mismatch: expected 1 (write), got {seen['wen']}"

    dut._log.info(f"object test passed: addr={addr:#05x}, data={data:#06x}, wen={seen['wen']}")


@cocotb.test()
async def test_dle(dut):
    """DLE test, 0x03 makes the next byte literal, sends it as an escaped data byte"""
    dut._log.info("start DLE test")

    # setup (clock + reset)
    clock = Clock(dut.clk, 40, units="ns")          # starts clock (25MHz)
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.uart_rx.value = 1                           # we're not even using this, so keep idle at 1
    dut.clkdiv_ctl.value = 0                        # clkdiv not even used, so keep floating at 0
    dut.clkdiv_data.value = 0
    dut.dut_io.rx_bytes.valid.value = 0
    dut.dut_io.rx_bytes.data.value = 0
    await ClockCycles(dut.clk, 5)                   # hold reset low for 5 cycles
    dut.rst_n.value = 1                             # release reset
    await ClockCycles(dut.clk, 2)                   # wait 2 cycles for things to settle, then parser live

    data = 0xAB03                                   # arbitrary test value with data low = 0x03 (DLE) to test escape
    addr = 0x055                                    # arbitrary test value (9 bits)
    data_low = data & 0xFF                          # grabs lower 8 bits -> 0x03
    data_high = (data >> 8) & 0xFF                  # shifts down, masks lower 8 bits -> 0xAB
    addr_low = addr & 0xFF                          # grabs lower 8 bits -> 0x55
    addr_high = (addr >> 8) & 0xFF                  # shifts down, masks lower 8 bits -> 0x00

    DLE = 0x03                                      # DLE byte, next byte is literal

    stream = [0x01, DLE, data_low, data_high, addr_low, addr_high]     # inject sram write msg, 4 payload bytes (SRAM_WRITE, data low / high, addr low / high), but addr low is escaped

    seen = {"wrote": False, "addr": None, "data": None, "wen": None}

    async def monitor_sram():
            while True:                                # infinite loop that checks if sram_req_valid is high on every clk edge
                await RisingEdge(dut.clk)
    
                if int(dut.sram_req_valid.value) == 1 and not seen["wrote"]:
                    seen["wrote"] = True
                    seen["addr"] = int(dut.sram_req_waddr.value)                     # captures addr value at moment of write
                    seen["data"] = int(dut.sram_req_wdata.value)                     # captures data value at moment of write
                    seen["wen"] = int(dut.sram_req_wen.value)                        # captures wen (write enable) value at moment of write
    
    cocotb.start_soon(monitor_sram())

    await send_bytes(dut, stream)                                               # inject the stream with the escaped byte
    await ClockCycles(dut.clk, 5)                                               # wait a few cycles for things to settle

    # the check
    assert seen["wrote"] == True, "sram write not seen after object message"
    assert seen["data"] == data, f"wdata mismatch: expected {data:#06x}, got {seen['data']:#06x}"
    assert seen["addr"] == addr, f"waddr mismatch: expected {addr:#05x}, got {seen['addr']:#05x}"
    assert seen["wen"] == 1, f"wen mismatch: expected 1 (write), got {seen['wen']}"

    dut._log.info(f"DLE escape ok: addr={addr:#05x}, data={data:#06x} delivered through escape, wen={seen['wen']}")


@cocotb.test()
async def test_dle_multiple(dut):
    """two escaped 0x03 bytes in 1 msg, escape flag must reset between them and stya aligned"""
    dut._log.info("start multi-DLE test")

    # setup (clock + reset)
    clock = Clock(dut.clk, 40, units="ns")          # starts clock (25MHz)
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.uart_rx.value = 1                           # we're not even using this, so keep idle at 1
    dut.clkdiv_ctl.value = 0                        # clkdiv not even used, so keep floating at 0
    dut.clkdiv_data.value = 0
    dut.dut_io.rx_bytes.valid.value = 0
    dut.dut_io.rx_bytes.data.value = 0
    await ClockCycles(dut.clk, 5)                   # hold reset low for 5 cycles
    dut.rst_n.value = 1                             # release reset
    await ClockCycles(dut.clk, 2)                   # wait 2 cycles for things to settle, then parser live

    data = 0xBE03                                   # data low = 0x03, needs esc
    addr = 0x003                                    # addr low = 0x03, needs esc
    data_low = data & 0xFF                          # 0x03
    data_high = (data >> 8) & 0xFF                  # 0xBE
    addr_low = addr & 0xFF                          # 0x03
    addr_high = (addr >> 8) & 0x01                  # 0x00

    DLE = 0x03

    # escape both 0x03 payload bytes (data_low and addr_low)
    stream = [0x01, DLE, data_low, data_high, DLE, addr_low, addr_high]

    seen = {"wrote": False, "addr": None, "data": None, "wen": None}

    async def monitor_sram():
        while True:                                 # infinite loop that checks if sram_req_valid is high on every clk edge
            await RisingEdge(dut.clk)

            if int(dut.sram_req_valid.value) == 1 and not seen["wrote"]:
                seen["wrote"] = True
                seen["addr"] = int(dut.sram_req_waddr.value)                     # captures addr value at moment of write
                seen["data"] = int(dut.sram_req_wdata.value)                     # captures data value at moment of write
                seen["wen"] = int(dut.sram_req_wen.value)                        # captures wen (write enable) value at moment of write

    cocotb.start_soon(monitor_sram())

    await send_bytes(dut, stream)                    # inject the stream with 2 escaped bytes
    await ClockCycles(dut.clk, 5)

    assert seen["wrote"] == True, "no sram write after a double escaped message"
    assert seen["data"] == data, f"wdata mismatch: expected {data:#06x}, got {seen['data']:#06x}"
    assert seen["addr"] == addr, f"waddr mismatch: expected {addr:#05x}, got {seen['addr']:#05x}"
    assert seen["wen"] == 1, f"wen mismatch: expected 1 (write), got {seen['wen']}"

    dut._log.info(f"multi-DLE test ok, two escaped 0x03 bytes delivered, data={data:#06x}, addr={addr:#05x}")


@cocotb.test()
async def test_invalid_start(dut):
    """invalid start byte test (not 0x00, 0x01, or 0x03), parser should ignore and recovers after"""
    dut._log.info("start invalid start byte test")

    # setup (clock + reset)
    clock = Clock(dut.clk, 40, units="ns")          # starts clock (25MHz)
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.uart_rx.value = 1                           # we're not even using this, so keep idle at 1
    dut.clkdiv_ctl.value = 0                        # clkdiv not even used, so keep floating at 0
    dut.clkdiv_data.value = 0
    dut.dut_io.rx_bytes.valid.value = 0
    dut.dut_io.rx_bytes.data.value = 0
    await ClockCycles(dut.clk, 5)                   # hold reset low for 5 cycles
    dut.rst_n.value = 1                             # release reset
    await ClockCycles(dut.clk, 2)                   # wait 2 cycles for things to settle, then parser live

    # the monitor: see if anything fires, and what was written to if it did
    seen = {"render": False, "sram": False, "addr": None, "data": None}

    async def watch():
        while True:                                 # infinite loop, checks both outputs on every clk edge
            await RisingEdge(dut.clk)

            if int(dut.render_strobe.value) == 1:
                seen["render"] = True               # flags if render ever pulses

            if int(dut.sram_req_valid.value) == 1 and not seen["sram"]:
                seen["sram"] = True                 # flags + capture the first sram write
                seen["addr"] = int(dut.sram_req_waddr.value)
                seen["data"] = int(dut.sram_req_wdata.value)

    cocotb.start_soon(watch())

    # sending in junk bytes (NOT 0x00 0x01 0x03)
    for junk in (0x42, 0x7F, 0x10):                   # arbitrary meaningless bytes           
        await send_bytes(dut, [junk])                 # inject junk byte, parser should ignore
    await ClockCycles(dut.clk, 5)                     # wait a few cycles for things to settle

    # the junk shouldve done nothing, parser idle, no outputs
    assert int(dut.dut_io.rx_state.value) == 0, f"parser left idle on junk (rx_state={int(dut.dut_io.rx_state.value)})"     # rx_idle == 0
    assert not seen["render"], "render pulsed on a junk byte"
    assert not seen["sram"], "sram wrote on a junk byte"

    # the check, a valid object must still parse
    seen["sram"] = False                                # reset ts so it detects a new write
    seen["addr"] = None
    seen["data"] = None

    data = 0x1234                                       # arbitrary test value (16 bits)
    addr = 0x007                                        # arbitrary test value (9 bits)
    data_low = data & 0xFF                              # grabs lower 8 bits -> 0x34
    data_high = (data >> 8) & 0xFF                      # shifts down, masks lower 8 bits -> 0x12
    addr_low = addr & 0xFF                              # grabs lower 8 bits -> 0x07
    addr_high = (addr >> 8) & 0xFF                      # shifts down, masks lower 8 bits -> 0x00

    await send_bytes(dut, [0x01, data_low, data_high, addr_low, addr_high])
    await ClockCycles(dut.clk, 5)

    # valid msg still went thru correctly
    assert seen["sram"], "valid object after junk failed to produce a write"
    assert seen["addr"] == addr, f"waddr wrong after junk, expected {addr:#05x}, got {seen['addr']:#05x}"
    assert seen["data"] == data, f"wdata wrong after junk, expected {data:#06x}, got {seen['data']:#06x}"

    dut._log.info("invalid start byte test ok, junk ignored, parser recovered")


@cocotb.test()
async def test_masked_bits(dut):
    """parser uses only the intended bits of each high byte, upper bits must not leak in"""
    dut._log.info("start masked bits test")

    # setup (clock + reset)
    clock = Clock(dut.clk, 40, units="ns")          # starts clock (25MHz)
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.uart_rx.value = 1                           # we're not even using this, so keep idle at 1
    dut.clkdiv_ctl.value = 0                        # clkdiv not even used, so keep floating at 0
    dut.clkdiv_data.value = 0
    dut.dut_io.rx_bytes.valid.value = 0
    dut.dut_io.rx_bytes.data.value = 0
    await ClockCycles(dut.clk, 5)                   # hold reset low for 5 cycles
    dut.rst_n.value = 1                             # release reset
    await ClockCycles(dut.clk, 2)                   # wait 2 cycles for things to settle, then parser live

    # the monitor that catches both outputs, sram for addr check, render for width check
    seen = {
        "sram": False, "addr": None, "data": None,
        "render": False, "w": None, "h": None,
    }

    async def watch():
        while True:                                 # infinite loop that checks both outputs on every clk edge
            await RisingEdge(dut.clk)

            if int(dut.sram_req_valid.value) == 1 and not seen["sram"]:
                seen["sram"] = True
                seen["addr"] = int(dut.sram_req_waddr.value)
                seen["data"] = int(dut.sram_req_wdata.value)

            if int(dut.render_strobe.value) == 1:  
                seen["render"] = True
                seen["w"] = int(dut.render_img_w.value)
                seen["h"] = int(dut.render_img_h.value)

    cocotb.start_soon(watch())

    # width check
    # the width high byte feeds only img_w[11:8] <= rx_byte_reg[3:0], so only the low nibble matters
    # send 0xF3 (upper nibble is trash, low nibble 0x3 is real top bits)
    # if parser used the wrong nibble then we'd get 0xFA5 instead of 0x3A5
    dim_low = 0xA5                                  # full low byte
    dim_high_byte = 0xF3                            # upper 0xF is garbage, low 0x3 is real top bits
    expected_dim = 0x3A5                            # = {0x3, 0xA5}, not 0xFA5

    await send_bytes(dut, [0x00, dim_low, dim_high_byte, dim_low, dim_high_byte])           # inject render msg
    await ClockCycles(dut.clk, 5)

    assert seen["render"], "render never pulsed"
    assert seen["w"] == expected_dim, f"img_w used wrong bits: expected {expected_dim:#05x}, got {seen['w']:#05x}"
    assert seen["h"] == expected_dim, f"img_h used wrong bits: expected {expected_dim:#05x}, got {seen['h']:#05x}"

    # addr check
    # the addr high byte feeds only addr[8] <= rx_byte_reg[0], so only bit 0 matters
    # send 0xFE (bit 0 = 0, others 1). 
    # if parser used any other bit, addr[8] would be 1, and get 0x1AA instead of 0x0AA
    data = 0x1234                                   # arbitrary data
    data_low = data & 0xFF                          # grabs lower 8 bits -> 0x34
    data_high = (data >> 8) & 0xFF                  # shifts down and masks -> 0x12
    addr_low = 0xAA                                 # full low byte
    addr_high_byte = 0xFE                           # bit 0 = 0, upper bits all 1
    expected_addr = 0x0AA                           # addr[8] must be 0, not 0x1AA

    await send_bytes(dut, [0x01, data_low, data_high, addr_low, addr_high_byte])    # inject obj msg
    await ClockCycles(dut.clk, 5)

    assert seen["sram"], "object never wrote"
    assert seen["data"] == data, f"wdata wrong: expected {data:#06x}, got {seen['data']:#06x}"
    assert seen["addr"] == expected_addr, f"addr used wrong bits: expected {expected_addr:#05x}, got {seen['addr']:#05x}"

    dut._log.info("masked bits test ok, only the intended bits of each high byte are used")


@cocotb.test()
async def test_render_extremes(dut):
    """render with min (0x000) and max (0xFFF) dims, both must come thru exactly"""
    dut._log.info("start render extremes test")

    # setup (clock + reset)
    clock = Clock(dut.clk, 40, units="ns")          # starts clock (25MHz)
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.uart_rx.value = 1                           # we're not even using this, so keep idle at 1
    dut.clkdiv_ctl.value = 0                        # clkdiv not even used, so keep floating at 0
    dut.clkdiv_data.value = 0
    dut.dut_io.rx_bytes.valid.value = 0
    dut.dut_io.rx_bytes.data.value = 0
    await ClockCycles(dut.clk, 5)                   # hold reset low for 5 cycles
    dut.rst_n.value = 1                             # release reset
    await ClockCycles(dut.clk, 2)                   # wait 2 cycles for things to settle, then parser live

    seen = {"w": None, "h": None}

    async def monitor_render():
        while True:                                 # infinite loop that checks if render_strobe is high on every clk edge 
            await RisingEdge(dut.clk)

            if int(dut.render_strobe.value) == 1:
                seen["w"] = int(dut.render_img_w.value)                     # captures img_w value at moment of pulse
                seen["h"] = int(dut.render_img_h.value)                     # captures img_h value at moment of pulse

    cocotb.start_soon(monitor_render())

    # loop over the boundary values
    for dim in (0x000, 0xFFF):
        dim_low = dim & 0xFF
        dim_high = (dim >> 8) & 0xFF

        await send_bytes(dut, [0x00, dim_low, dim_high, dim_low, dim_high])
        await ClockCycles(dut.clk, 5)

        assert seen["w"] == dim, f"img_w wrong at extreme: expected {dim:#05x}, got {seen['w']:#05x}"
        assert seen["h"] == dim, f"img_h wrong at extreme: expected {dim:#05x}, got {seen['h']:#05x}"

    dut._log.info("render extremes ok, 0x000 and 0xFFF both correct")


@cocotb.test()
async def test_object_extremes(dut):
    """object with min (data 0x0000 / addr 0x000) and max (data 0xFFFF / addr 0x1FF), both exact"""
    dut._log.info("start object extremes test")

    # setup (clock + reset)
    clock = Clock(dut.clk, 40, units="ns")          # starts clock (25MHz)
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.uart_rx.value = 1                           # we're not even using this, so keep idle at 1
    dut.clkdiv_ctl.value = 0                        # clkdiv not even used, so keep floating at 0
    dut.clkdiv_data.value = 0
    dut.dut_io.rx_bytes.valid.value = 0
    dut.dut_io.rx_bytes.data.value = 0
    await ClockCycles(dut.clk, 5)                   # hold reset low for 5 cycles
    dut.rst_n.value = 1                             # release reset
    await ClockCycles(dut.clk, 2)                   # wait 2 cycles for things to settle, then parser live

    seen = {"addr": None, "data": None}

    async def monitor_sram():
        while True:                                # infinite loop that checks if sram_req_valid is high on every clk edge
            await RisingEdge(dut.clk)

            if int(dut.sram_req_valid.value) == 1:
                seen["addr"] = int(dut.sram_req_waddr.value)                     # captures addr value at moment of write
                seen["data"] = int(dut.sram_req_wdata.value)                     # captures data value at moment of write
    
    cocotb.start_soon(monitor_sram())

    # (data, addr) boundary pairs: all 0, then all 1 
    for data, addr in ((0x0000, 0x000), (0xFFFF, 0x1FF)):
        data_low = data & 0xFF
        data_high = (data >> 8) & 0xFF
        addr_low = addr & 0xFF
        addr_high = (addr >> 8) & 0xFF

        await send_bytes(dut, [0x01, data_low, data_high, addr_low, addr_high])
        await ClockCycles(dut.clk, 5)

        assert seen["data"] == data, f"wdata wrong at extreme: expected {data:#06x}, got {seen['data']:#06x}"
        assert seen["addr"] == addr, f"waddr wrong at extreme: expected {addr:#05x}, got {seen['addr']:#05x}"

    dut._log.info("object extremes ok, min and max data / addr both correct")


@cocotb.test()
async def test_b2b(dut):
    """sending back to back valid messages with no gap, both should land"""
    dut._log.info("start b2b message test")

    # setup (clock + reset)
    clock = Clock(dut.clk, 40, units="ns")          # starts clock (25MHz)
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.uart_rx.value = 1                           # we're not even using this, so keep idle at 1
    dut.clkdiv_ctl.value = 0                        # clkdiv not even used, so keep floating at 0
    dut.clkdiv_data.value = 0
    dut.dut_io.rx_bytes.valid.value = 0
    dut.dut_io.rx_bytes.data.value = 0
    await ClockCycles(dut.clk, 5)                   # hold reset low for 5 cycles
    dut.rst_n.value = 1                             # release reset
    await ClockCycles(dut.clk, 2)                   # wait 2 cycles for things to settle, then parser live

    # the monitor that catches both outputs, msg 1 writes to sram, msg 2 pulses render
    seen = {
        "sram": False, "addr": None, "data": None,
        "render": False, "w": None, "h": None,
    }

    async def watch():
        while True:                                 # infinite loop that checks both outputs on every clk edge
            await RisingEdge(dut.clk)

            if int(dut.sram_req_valid.value) == 1 and not seen["sram"]:
                seen["sram"] = True                 # flag and capture the first sram write from msg 1
                seen["addr"] = int(dut.sram_req_waddr.value)
                seen["data"] = int(dut.sram_req_wdata.value)

            if int(dut.render_strobe.value) == 1:  
                seen["render"] = True               # flag and capture the render pulse from msg 2
                seen["w"] = int(dut.render_img_w.value)
                seen["h"] = int(dut.render_img_h.value)

    cocotb.start_soon(watch())

    # 1st msg (object)
    obj_data = 0xBEEF                               # arbitrary test value (16 bits)
    obj_addr = 0x111                                # arbitrary test value (9 bits)
    obj_data_low = obj_data & 0xFF                  # grabs lower 8 bits -> 0xEF
    obj_data_high = (obj_data >> 8) & 0xFF          # shifts down, masks lower 8 bits -> 0xBE
    obj_addr_low = obj_addr & 0xFF                  # grabs lower 8 bits -> 0x11
    obj_addr_high = (obj_addr >> 8) & 0xFF          # shifts down, masks lower 8 bits -> 0x01

    await send_bytes(dut, [0x01, obj_data_low, obj_data_high, obj_addr_low, obj_addr_high])     # inject object msg

    # 2nd msg (render), the b2b part w no gap
    dim = 0x2A5                                     # arbitrary test value (12 bits)
    dim_low = dim & 0xFF                            # grabs lower 8 bits -> 0xA5
    dim_high = (dim >> 8) & 0xFF                    # shift down, masks lower 8 bits -> 0x02

    await send_bytes(dut, [0x00, dim_low, dim_high, dim_low, dim_high])     # inject render msg
    await ClockCycles(dut.clk, 5)                                           # wait a few cycles for things to settle
    
    # check 1st msg landed correctly
    assert seen["sram"], "first object message produced no write"
    assert seen["addr"] == obj_addr, f"obj waddr wrong: expected {obj_addr:#05x}, got {seen['addr']:#05x}"
    assert seen["data"] == obj_data, f"obj wdata wrong: expected {obj_data:#06x}, got {seen['data']:#06x}"

    # check 2nd msg landed correctly, proves parser reset its state after msg 1
    assert seen["render"], "second render message produced no pulse"
    assert seen["w"] == dim, f"render w wrong: expected {dim:#05x}, got {seen['w']:#05x}"
    assert seen["h"] == dim, f"render h wrong: expected {dim:#05x}, got {seen['h']:#05x}"

    dut._log.info("back to back messages test ok, parser recieved both")


@cocotb.test()
async def test_backpressure(dut):
    """sram not ready: write req must be held until req_ready goes high"""
    dut._log.info("start backpressure test")

    # setup (clock + reset)
    clock = Clock(dut.clk, 40, units="ns")          # starts clock (25MHz)
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.uart_rx.value = 1                           # we're not even using this, so keep idle at 1
    dut.clkdiv_ctl.value = 0                        # clkdiv not even used, so keep floating at 0
    dut.clkdiv_data.value = 0
    dut.dut_io.rx_bytes.valid.value = 0
    dut.dut_io.rx_bytes.data.value = 0
    await ClockCycles(dut.clk, 5)                   # hold reset low for 5 cycles
    dut.rst_n.value = 1                             # release reset
    await ClockCycles(dut.clk, 2)                   # wait 2 cycles for things to settle, then parser live

    # make sram busy -> it will not accept writes
    dut.sram_req_ready_drv.value = 0

    data = 0xCAFE                                   # arbitrary test value (16 bits)
    addr = 0x0AA                                    # arbitrary test value (9 bits)
    data_low = data & 0xFF                          # grabs lower 8 bits -> 0xFE
    data_high = (data >> 8) & 0xFF                  # shifts down and masks lower 8 -> 0xCA
    addr_low = addr & 0xFF                          # grabs lower 8 bits -> 0xAA
    addr_high = (addr >> 8) & 0x01                  # only bit 0 -> 0x00

    await send_bytes(dut, [0x01, data_low, data_high, addr_low, addr_high])         # inject object msg
    await ClockCycles(dut.clk, 5)                                                   # let the write request assert

    # the write must be pending + held, since sram hasnt accepted it 
    assert int(dut.sram_req_valid.value) == 1, "req_valid should be held high while sram not ready"
    assert int(dut.sram_req_waddr.value) == addr, f"waddr wrong: expected {addr:#05x}, got {int(dut.sram_req_waddr.value):#05x}"
    assert int(dut.sram_req_wdata.value) == data, f"wdata wrong: expected {data:#06x}, got {int(dut.sram_req_wdata.value):#06x}"

    # wait even longer to see if it's still held (not wrongly cleared = write would be lost)
    await ClockCycles(dut.clk, 10)
    assert int(dut.sram_req_valid.value) == 1, "req_valid dropped while sram still not ready (write lost)"

    # now let sram accept the write
    dut.sram_req_ready_drv.value = 1
    await ClockCycles(dut.clk, 5)

    # the write should be accepted, req_valid clears
    assert int(dut.sram_req_valid.value) == 0, "req_valid should clear after sram accepts write"

    dut._log.info("backpressure test ok, write held while not ready, completed when ready")
