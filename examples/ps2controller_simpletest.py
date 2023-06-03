# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Tod Kurt
#
# SPDX-License-Identifier: Unlicense

import time
import board
from ps2controller import PS2Controller

# one way to wire this up, for example on a Pico
controller = PS2Controller( dat=board.GP2, cmd=board.GP3, att=board.GP4, clk=board.GP5 )

print("hi press buttons")
while True:
    events = ps2x.update()
    if events:
        print("events", events, int(dt*1000) )
        print("sticks: L:", ps2x.analog_left(), "R:", ps2x.analog_right() )
