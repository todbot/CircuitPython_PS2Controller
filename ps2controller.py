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

* Sony PS2 Controller or compatible gamepad


**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads


"""

# imports

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/todbot/CircuitPython_PS2Controller.git"


from collections import namedtuple
import time
from micropython import const
import digitalio

# config strings sent to the controller
_enter_config = (0x01, 0x43, 0x00, 0x01, 0x00)
_set_mode = (0x01, 0x44, 0x00, 0x01, 0x03, 0x00, 0x00, 0x00, 0x00)
_set_bytes_large = (0x01, 0x4F, 0x00, 0xFF, 0xFF, 0x03, 0x00, 0x00, 0x00)
_exit_config = (0x01, 0x43, 0x00, 0x00, 0x5A, 0x5A, 0x5A, 0x5A, 0x5A)
# _enable_rumble = (0x01, 0x4D, 0x00, 0x00, 0x01)
_enable_rumble = (0x01, 0x4D, 0x00, 0x01, 0x01, 0xFF, 0xFF, 0xFF, 0xFF)
_type_read = (0x01, 0x45, 0x00, 0x5A, 0x5A, 0x5A, 0x5A, 0x5A, 0x5A)

_CTRL_BYTE_DELAY_MICROS = const(4)  # microseconds
_CTRL_CLK_DELAY_MICROS = const(5)  # microseconds


def _delay_micros(usec):
    time.sleep(usec / 1_000_000)


def _delay_millis(msec):
    time.sleep(msec / 1_000)


#
PS2ButtonEvent = namedtuple("PS2ButtonEvent", ("id", "pressed", "released", "name"))


# pylint: disable-msg=(invalid-name, too-few-public-methods)
class PS2Button:
    """PS2 Button constants mapping button name to number"""

    SELECT = 0
    L3 = 1
    R3 = 2
    START = 3
    UP = 4
    RIGHT = 5
    DOWN = 6
    LEFT = 7
    L2 = 8
    R2 = 9
    L1 = 10
    R1 = 11
    TRIANGLE = 12
    CIRCLE = 13
    CROSS = 14
    SQUARE = 15

    # fmt: off
    button_to_analog_id = (-1, -1, -1, -1, 11, 9, 12, 10, 19, 20, 17, 18, 13, 14, 15, 16)

    names = ("SELECT", "L3", "R3", "START", "UP", "RIGHT", "DOWN", "LEFT",
             "L2", "R2", "L1", "R1", "TRIANGLE", "CIRCLE", "CROSS", "SQUARE")
    # fmt: on


# pylint: enable-msg=(invalid-name, too-few-public-methods)


class PS2Controller:  # pylint: disable=too-many-instance-attributes
    """
    Driver to read and control a Sony PS2 controller

    :param ~microcontroller.Pin clk: PS2 clock pin (blue wire)
    :param ~microcontroller.Pin cmd: PS2 command pin (orange wire)
    :param ~microcontroller.Pin att: PS2 attention pin (yellow wire)
    :param ~microcontroller.Pin dat: PS2 data pin (brown wire)
    :param bool enable_pressure: True to enable reading analog button pressure
    :param bool enable_rumble: True to enable controlling rumble motors
                                 (needs extra voltage and current)
    """

    def __init__(
        self, clk, cmd, att, dat, enable_pressure=False, enable_rumble=False
    ):  # pylint: disable=(too-many-arguments)
        self.clk_pin = digitalio.DigitalInOut(clk)
        self.att_pin = digitalio.DigitalInOut(att)
        self.cmd_pin = digitalio.DigitalInOut(cmd)
        self.dat_pin = digitalio.DigitalInOut(dat)
        self.clk_pin.switch_to_output(value=False)
        self.att_pin.switch_to_output(value=False)
        self.cmd_pin.switch_to_output(value=False)
        self.dat_pin.switch_to_input(pull=digitalio.Pull.UP)

        self.ps2data = [0] * 21  # holds raw data from controller

        self.enable_pressure = enable_pressure
        self.enable_rumble = enable_rumble
        self.rumble_motors = [0, 0]  # left, right?

        self._read_delay_millis = 1

        self.cmd_pin.value = True  # CMD_SET()
        self.clk_pin.value = True  # CLK_SET()

        self._buttons = 0
        self._last_buttons = 0

        if not self._config_gamepad():
            print("could not configure controller")
            return  # TODO: throw exception?
        self.update()  # get initial values

    def update(self):
        """Read the controller and return a list of PS2ButtonEvents"""
        self._read_gamepad()

        self._last_buttons = self._buttons
        self._buttons = self.ps2data[4] << 8 | self.ps2data[3]

        events = []
        for i in range(16):
            if self._last_buttons & (1 << i) != self._buttons & (1 << i):
                pressed = (self._buttons & (1 << i)) == 0
                released = not pressed
                events.append(PS2ButtonEvent(i, pressed, released, PS2Button.names[i]))
        return events

    def buttons(self):
        """Return a 16-bit bitfield of the state of all buttons"""
        return self._buttons

    def button(self, button_id):
        """Return True if button is currently pressed
        :param int button_id: 0-15 id number from PS2ButtonEvent.id or PS2Button.*
        """
        return (self._buttons & (1 << button_id)) == 0

    def analog_button(self, button_id):
        """Return analog pressure value for button
        :param int button_id 0-15 id number PS2ButtonEvent.id or PS2Button.*
        """
        return self.ps2data[PS2Button.button_to_analog_id[button_id]] / 255

    def analog_right(self):
        """Return a (x,y) tuple of the right analog stick"""
        return (self.ps2data[5], self.ps2data[6])

    def analog_left(self):
        """Return a (x,y) tuple of the left analog stick"""
        return (self.ps2data[7], self.ps2data[8])

    def set_rumble(self, motor_num, strength):
        """
        Set rumble motor strength. Set on next update() call.
        :param int motor_num: whiich motor to affect: 0, 1
        :param float stregnth amount of rumble, 0-1
        """
        self.rumble_motors[motor_num] = min(max(strength, 0), 1)

    def _config_gamepad(self):
        # "new error checking. First, read gamepad a few times to see if it's talking"
        self._read_gamepad()
        self._read_gamepad()

        if self.ps2data[1] not in (0x41, 0x42, 0x73, 0x79):
            print("PS2Controller mode not matched or no controller found")
            print("\tExpected 0x41,0x42,0x73,0x79 but got %02x" % self.ps2data[1])
            return False

        for _ in range(10):
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
            if self.enable_rumble:
                self._send_command_string(_enable_rumble)
            if self.enable_pressure:
                self._send_command_string(_set_bytes_large)
            self._send_command_string(_exit_config)

            self._read_gamepad()

            if self.enable_pressure:
                if self.ps2data[1] == 0x79:
                    return True
                # TODO: handle case where will not switch to pressure mode

            if self.ps2data[1] == 0x73:
                return True

            # "add 1ms to read_delay"
            self._read_delay_millis += 1
            print("P2SController: could not configure, inreasing read_delay_millis")

        # couldn't get controller to do what we wanted
        print("PS2Controller: Controller not accepting commands.")
        print("\tMode still at %02x" % self.ps2data[1])
        return False

    def _read_gamepad(self):  # motor1=False, motor2=False):
        motor1_val = int(self.rumble_motors[0] * 255)
        motor2_val = int(self.rumble_motors[1] * 255)

        dword1 = (0x01, 0x42, 0, motor1_val, motor2_val, 0, 0, 0, 0)  # 9 values
        dword2 = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)  # 12 values, all zero

        retry_count = 5
        for _ in range(retry_count):
            self.cmd_pin.value = True
            self.clk_pin.value = True
            self.att_pin.value = False  # "LOW enable joystick"  (this is chip select)

            _delay_micros(_CTRL_BYTE_DELAY_MICROS)

            # "Send the command to send button and joystick data"
            for i in range(9):
                self.ps2data[i] = self._gamepad_shiftinout(dword1[i])

            # "if controller is in full data return mode, get the rest of data"
            if self.ps2data[1] == 0x79:  # 0x79 == Dual Shock 2
                for i in range(12):
                    self.ps2data[9 + i] = self._gamepad_shiftinout(dword2[i])

            self.att_pin.value = True  # "HIGH disable joystick"

            # "Check to see if we received valid data or not."
            # "We should be in analog mode for our data to be valid (analog == 0x7_)"
            if self.ps2data[1] & 0xF0 == 0x70:
                # print("PS2Controller: we are in analog mode good!")
                break

            # "If we got to here, we are not in analog mode, try to recover..."
            self._reconfig_gamepad()
            # "try to get back into Analog mode."
            _delay_micros(self._read_delay_millis)

    def _reconfig_gamepad(self):
        self._send_command_string(_enter_config)
        self._send_command_string(_set_mode)
        if self.enable_rumble:
            self._send_command_string(_enable_rumble)
        if self.enable_pressure:
            self._send_command_string(_set_bytes_large)
        self._send_command_string(_exit_config)

    def _send_command_string(self, cmdstr):
        self.att_pin.value = False  # "low enable joystick"
        _delay_micros(_CTRL_BYTE_DELAY_MICROS)
        for byte in cmdstr:
            self._gamepad_shiftinout(byte)
        self.att_pin.value = True  # "high disable joystick
        _delay_millis(self._read_delay_millis)

    def _gamepad_shiftinout(self, byte_out):
        byte_in = 0
        for i in range(8):  # foreach bit in byte
            self.cmd_pin.value = (byte_out & (1 << i)) != 0  # send data out on cmd pin
            self.clk_pin.value = False  # lower clock to transmit bit
            _delay_micros(_CTRL_CLK_DELAY_MICROS)
            if self.dat_pin.value:  # read data in
                byte_in |= 1 << i
            self.clk_pin.value = True  # raise clock to signal end of bit write/read
            _delay_micros(_CTRL_CLK_DELAY_MICROS)
        self.cmd_pin.value = True  # return cmd pin back to idle
        _delay_micros(_CTRL_BYTE_DELAY_MICROS)
        return byte_in
