# SPDX-FileCopyrightText: Copyright (c) 2023 Tod Kurt
#
# SPDX-License-Identifier: MIT

import board
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from ps2controller import PS2Controller

buttons_to_keys = {
    "UP": (Keycode.W,),  # WASD for D-pad
    "DOWN": (Keycode.S,),
    "LEFT": (Keycode.A,),
    "RIGHT": (Keycode.D,),
    "TRIANGLE": (Keycode.K,),  # HJKL for action buttons
    "CROSS": (Keycode.J,),
    "SQUARE": (Keycode.H,),
    "CIRCLE": (Keycode.L,),
}

keyboard = Keyboard(usb_hid.devices)

# one way to wire this up, for example on a Pico
ps2 = PS2Controller(dat=board.GP2, cmd=board.GP3, att=board.GP4, clk=board.GP5)

print("hi, press buttons")
while True:
    events = ps2.update()
    if events:
        print("events", events)
        for event in events:
            # find keys to send for button, undefined buttons send SPACE
            keycodes = buttons_to_keys.get(event.name, (Keycode.SPACE,))
            if event.pressed:
                keyboard.press(*keycodes)
            elif event.released:
                keyboard.release(*keycodes)
