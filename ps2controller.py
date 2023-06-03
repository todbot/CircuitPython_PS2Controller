# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Tod Kurt
#
# SPDX-License-Identifier: MIT
"""
`ps2controller`
================================================================================

CircuitPython library to read Sony PS2 game controllers


* Author(s): Tod Kurt

Implementation Notes
--------------------

**Hardware:**

.. todo:: Add links to any specific hardware product page(s), or category page(s).
  Use unordered list & hyperlink rST inline format: "* `Link Text <url>`_"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

.. todo:: Uncomment or remove the Bus Device and/or the Register library dependencies
  based on the library's use of either.

# * Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
# * Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

# imports

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/todbot/CircuitPython_PS2Controller.git"


import time
import digitalio
from collections import namedtuple
from micropython import const

# magic config strings sent to the controller
_enter_config    = (0x01,0x43,0x00,0x01,0x00)
_set_mode        = (0x01,0x44,0x00,0x01,0x03,0x00,0x00,0x00,0x00)
_set_bytes_large = (0x01,0x4F,0x00,0xFF,0xFF,0x03,0x00,0x00,0x00)
_exit_config     = (0x01,0x43,0x00,0x00,0x5A,0x5A,0x5A,0x5A,0x5A)
_enable_rumble   = (0x01,0x4D,0x00,0x00,0x01)
_type_read       = (0x01,0x45,0x00,0x5A,0x5A,0x5A,0x5A,0x5A,0x5A)

_CTRL_BYTE_DELAY_MICROS = 4   # microseconds
_CTRL_CLK_DELAY_MICROS  = 5  # microseconds

def _delay_micros(us): time.sleep(us/1_000_000)
def _delay_millis(ms): time.sleep(ms/1_000)

ButtonEvent = namedtuple("ButtonEvent", ("number", "presssed", "released", "name"))

button_names = ("SELECT", "L3", "R3", "START", "UP", "RIGHT", "DOWN", "LEFT",
                "L2", "R2", "L1", "R1", "TRIANGLE", "CIRCLE", "CROSS", "SQUARE")

class PS2Controller:

    # config gamepad
    def __init__(self, clk, cmd, att, dat, read_pressure=False, rumbling=False):
        self.clk_pin = digitalio.DigitalInOut(clk)
        self.att_pin = digitalio.DigitalInOut(att)
        self.cmd_pin = digitalio.DigitalInOut(cmd)
        self.dat_pin = digitalio.DigitalInOut(dat)
        self.clk_pin.switch_to_output(value=False)
        self.att_pin.switch_to_output(value=False)
        self.cmd_pin.switch_to_output(value=False)
        self.dat_pin.switch_to_input(pull=digitalio.Pull.UP)

        self.ps2data = [0] * 21  # holds raw data from controller

        self._read_delay_millis = 1

        self.cmd_pin.value = True  # CMD_SET()
        self.clk_pin.value = True  # CLK_SET()

        self._buttons = 0
        self._last_buttons = 0

        if not self._config_gamepad():
            print("could not configure controller")
            return  # FIXME: throw exception?
        self.update()  # get initial values

    def update(self):
        """Read the controller and return a list of ButtonEvents"""
        self._read_gamepad()

        self._last_buttons = self._buttons
        self._buttons = self.ps2data[4] << 8 | self.ps2data[3]

        events = []
        for i in range(16):
            if self._last_buttons & (1<<i) != self._buttons & (1<<i):
                pressed = (self._buttons & (1<<i)) == 0
                released = not pressed
                events.append( ButtonEvent(i, pressed, released, button_names[i] ) )
        return events

    def buttons(self):
        """Return a 16-bit bitfield of the state of all buttons"""
        return self._buttons

    def analog_right(self):
        """Return a (x,y) tuple of the right analog stick"""
        return (self.ps2data[5], self.ps2data[6])

    def analog_left(self):
        """Return a (x,y) tuple of the left analog stick"""
        return (self.ps2data[7], self.ps2data[8])


    def _config_gamepad(self):

        # "new error checking. First, read gamepad a few times to see if it's talking"
        self._read_gamepad()
        self._read_gamepad()

        if (self.ps2data[1] != 0x41 and
            self.ps2data[1] != 0x42 and
            self.ps2data[1] != 0x73 and
            self.ps2data[1] != 0x79):
            print("Controller mode not matched or no controller found")
            return False

        for y in range(10):
            self._send_command_string(_enter_config)

            # read type
            _delay_micros(_CTRL_BYTE_DELAY_MICROS)

            self.cmd_pin.value = True
            self.clk_pin.value = True
            self.att_pin.value = False  # "LOW enable joystick"
            _delay_micros(_CTRL_BYTE_DELAY_MICROS)

            temp = [0] * len(_type_read)
            for i in range(9):
                temp[i] = self._gamepad_shiftinout(_type_read[i])

            self.att_pin.value = False  # "HIGH disable joytick" (raise CS, that is)

            self.controller_type = temp[3]
            self._send_command_string(_set_mode)
            self._send_command_string(_exit_config)
            self._read_gamepad()

            if self.ps2data[1] == 0x73:
                return True

            # "add 1ms to read_delay"
            self._read_delay_millis += 1
            print("P2SX: upping read_delay_millis")

        # couldn't get controller to do what we wanted
        print("PS2Controller: Controller not accepting commands. Mode still set at %02x" % self.ps2data[1])
        return False

    def _read_gamepad(self, motor1=False, motor2=False):

        # if time.monotonic() - self._last_read > 1.5:
        #   self._reconfig_gamepad()

        motor1_val = 0  # tbd
        motor2_val = 0  # tbd

        dword1 = (0x01, 0x42, 0, motor1_val, motor2_val, 0,0,0,0)  # 9 values
        dword2 = (0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0)  # 12 values, all zero

        retry_count = 5
        for retry in range(retry_count):
            self.cmd_pin.value = True
            self.clk_pin.value = True
            self.att_pin.value = False  # "LOW enable joystick"  (this is chip select)

            _delay_micros(_CTRL_BYTE_DELAY_MICROS)

            # "Send the command to send button and joystick data"
            for i in range(9):
                self.ps2data[i] = self._gamepad_shiftinout(dword1[i])

            # "if controller is in full data return mode, get the rest of data"
            if self.ps2data[1] == 0x79:
                for i in range(12):
                    self.ps2data[9+i] = self._gamepad_shiftinout(dword2[i])

            self.att_pin.value = True  # "HIGH disable joystick"

            # "Check to see if we received valid data or not."
	        # "We should be in analog mode for our data to be valid (analog == 0x7_)"
            if self.ps2data[1] & 0xf0 == 0x70:
                #print("PS2Controller: we are in analog mode good!")
                break

            # "If we got to here, we are not in analog mode, try to recover..."
            self._reconfig_gamepad(); # "try to get back into Analog mode."
            _delay_micros( self._read_delay_millis )

    def _reconfig_gamepad(self):
        self._send_command_string(_enter_config)
        self._send_command_string(_set_mode)
        #if enable_rumble:
        # self._send_command_string(_enable_rumble)
        #if enable_pressures:
        # self._send_command_string(_set_bytes_large)
        self._send_command_string(_exit_config)

    def _send_command_string(self,cmdstr):
        self.att_pin.value = False  # "low enable joystick"
        _delay_micros(_CTRL_BYTE_DELAY_MICROS)
        for i in range(len(cmdstr)):
            self._gamepad_shiftinout(cmdstr[i])
        self.att_pin.value = True   # "high disable joystick
        _delay_millis( self._read_delay_millis )

    def _gamepad_shiftinout(self,byte_out):
        byte_in = 0
        for i in range(8):          # foreach bit in byte
            self.cmd_pin.value = (byte_out & (1<<i)) != 0  # send data out on cmd pin
            self.clk_pin.value = False  # lower clock to transmit bit
            _delay_micros(_CTRL_CLK_DELAY_MICROS)
            if self.dat_pin.value:  # read data in
                byte_in |= (1<<i)
            self.clk_pin.value = True  # raise clock to signal end of bit write/read
            _delay_micros(_CTRL_CLK_DELAY_MICROS)
        self.cmd_pin.value = True  # return cmd pin back to idle
        _delay_micros(_CTRL_BYTE_DELAY_MICROS)
        return byte_in
