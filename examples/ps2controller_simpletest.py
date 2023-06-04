# SPDX-FileCopyrightText: Copyright (c) 2023 Tod Kurt
#
# SPDX-License-Identifier: Unlicense

import board
from ps2controller import PS2Controller

# one way to wire this up, for example on a Pico
ps2 = PS2Controller(dat=board.GP2, cmd=board.GP3, att=board.GP4, clk=board.GP5)

print("hi press buttons")
while True:
    events = ps2.update()
    if events:
        print("events", events)
        print("sticks: L:", ps2.analog_left(), "R:", ps2.analog_right())
