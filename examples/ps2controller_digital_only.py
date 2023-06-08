# SPDX-FileCopyrightText: Copyright (c) 2023 Tod Kurt
#
# SPDX-License-Identifier: Unlicense

import time
import board
from ps2controller import PS2Controller

# one way to wire this up, for example on a Pico
ps2 = PS2Controller(
    dat=board.GP2,
    cmd=board.GP3,
    att=board.GP4,
    clk=board.GP5,
    enable_sticks=False,
    enable_rumble=False,
    enable_pressure=False,
)


def hexify(buf):
    """Print a byte array as a hex string"""
    if buf is None:
        return "None"
    return " ".join("%02x" % v for v in buf)


while True:
    time.sleep(0.1)
    dt = time.monotonic()
    events = ps2.update()
    dt = time.monotonic() - dt

    print("dt:%3d" % (dt * 1000), "data(%d):" % len(ps2.data), hexify(ps2.data))
