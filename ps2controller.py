# SPDX-FileCopyrightText: Copyright (c) 2023 Tod Kurt
#
# SPDX-License-Identifier: MIT
"""
`ps2controller`
================================================================================

CircuitPython library to read Sony PS1 and PS2 wired game controllers


* Author(s): Tod Kurt

Implementation Notes
--------------------

**Hardware:**

* Sony PS1 or PS2 controller or compatible device


**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads


"""

from collections import namedtuple
import time
from micropython import const
import digitalio

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/todbot/CircuitPython_PS2Controller.git"


# Time between att being issues to control and first clock edge
_ATTN_DELAY_MICROS = const(40)
# hold time for dat/cmd pins after clk
_HOLD_TIME_MICROS = const(2)
# Delay between bytes sent
_BYTE_DELAY_MICROS = const(2)
# Commands are sent to the controller repeatedly, until they succeed or time out
_COMMAND_TIMEOUT_SECS = 0.25
# Delay to wait after switching controllerl mode
_MODE_SWITCH_DELAY_SECS = 0.50

# fmt: off
# Command to enter the controller configuration (also known as \a escape) mode
_enter_config  = (0x01, 0x43, 0x00, 0x01, 0x5A)
_exit_config   = (0x01, 0x43, 0x00, 0x00, 0x5A)
_type_read     = (0x01, 0x45, 0x00)
_set_mode      = (0x01, 0x44, 0x00, 0x01, 0x03, 0x00, 0x00, 0x00, 0x00)
_enable_rumble = (0x01, 0x4D, 0x00, 0x00, 0x01)
_set_pressures = (0x01, 0x4F, 0x00, 0xFF, 0xFF, 0x03, 0x00, 0x00, 0x00)
# Command to read status of all buttons, 3 & 4 are rumble vals
_poll_rumble   = (0x01, 0x42, 0x00, 0xFF, 0xFF)
# Command to read status of all buttons.
_poll          = (0x01, 0x42, 0x00)
# fmt: on


def _is_valid_reply(status):
    return status[1] != 0xFF and (status[2] == 0x5A or status[2] == 0x00)


def _is_config_reply(status):
    return (status[1] & 0xF0) == 0xF0


def _get_reply_length(status):
    """Returns length of a command reply from controller status"""
    return (status[1] & 0x0F) * 2


def _delay_micros(usec):
    """Sleep the given number of microseconds, likely not accurate"""
    time.sleep(usec / 1_000_000)


def _hexify(buf):
    """Print a byte array as a hex string"""
    if buf is None:
        return "None"
    return " ".join("%02x" % v for v in buf)


PS2ButtonEvent = namedtuple("PS2ButtonEvent", ("id", "pressed", "released", "name"))
""" The event 'objects' returned by ps2.update()"""


# pylint: disable-msg=(invalid-name, too-few-public-methods)
class PS2Button:
    """PS2 Button constants mapping button name to number"""

    SELECT = 0
    """SELECT button, digital only"""
    L3 = 1
    """L3 button (left stick push), digital only"""
    R3 = 2
    """R3 button (right stick push), digital only"""
    START = 3
    """START button, digital only (pressure)"""
    UP = 4
    """D-pad UP, digital and analog (pressure)"""
    RIGHT = 5
    """D-pad RIGHT, digital and analog (pressure)"""
    DOWN = 6
    """D-pad DOWN, digital and analog (pressure)"""
    LEFT = 7
    """D-pad LEFT, digital and analog (pressure)"""
    L2 = 8
    """Left lower shoulder trigger button, digital and analog (pressure)"""
    R2 = 9
    """Right lower shoulder trigger button, digital and analog (pressure)"""
    L1 = 10
    """Left upper shoulder trigger button, digital and analog (pressure)"""
    R1 = 11
    """Right upper shoulder trigger button, digital and analog (pressure)"""
    TRIANGLE = 12
    """Triangle (green) action button, digital and analog (pressure)"""
    CIRCLE = 13
    """Circle (red) action button, digital and analog (pressure)"""
    CROSS = 14
    """Cross (blue) action button, digital and analog (pressure)"""
    SQUARE = 15
    """Square (pink) action button, digital and analog (pressure)"""

    # fmt: off
    """Map digital button id to analog id (not all buttons are pressure)"""
    button_to_analog_id = (-1, -1, -1, -1, 11, 9, 12, 10, 19, 20, 17, 18, 13, 14, 15, 16)

    """Map digital button id to button name"""
    names = ("SELECT", "L3", "R3", "START", "UP", "RIGHT", "DOWN", "LEFT",
             "L2", "R2", "L1", "R1", "TRIANGLE", "CIRCLE", "CROSS", "SQUARE")
    # fmt: on


class PS2Controller:  # pylint: disable=too-many-instance-attributes
    """
    Driver to read and control a Sony PS1 or PS2 wired controller

    :param ~microcontroller.Pin clk: PS2 clock pin (blue wire)
    :param ~microcontroller.Pin cmd: PS2 command pin (orange wire)
    :param ~microcontroller.Pin att: PS2 attention pin (yellow wire)
    :param ~microcontroller.Pin dat: PS2 data pin (brown wire)
    :param bool enable_sticks: True to enable analog sticks
                                 (otherwise faster digital only reads)
    :param bool enable_rumble: True to enable controlling rumble motors
                                 (needs extra voltage and current)
    :param bool enable_pressue: True to enable reading analog button pressure

    """

    def __init__(
        self,
        clk,
        cmd,
        att,
        dat,
        enable_sticks=True,
        enable_rumble=False,
        enable_pressure=False,
    ):  # pylint: disable=(too-many-arguments)
        self.clk_pin = digitalio.DigitalInOut(clk)
        self.att_pin = digitalio.DigitalInOut(att)
        self.cmd_pin = digitalio.DigitalInOut(cmd)
        self.dat_pin = digitalio.DigitalInOut(dat)
        self.clk_pin.switch_to_output(value=True)
        self.att_pin.switch_to_output(value=True)
        self.cmd_pin.switch_to_output(value=True)
        self.dat_pin.switch_to_input(pull=digitalio.Pull.UP)

        self.enable_sticks = enable_sticks
        self.enable_rumble = enable_rumble
        self.enable_pressure = enable_pressure

        self._last_dt = 0
        self._buttons = 0
        self._last_buttons = 0

        self.motor1_level = 0  # 0-255, 40 is where motor starts moving
        self.motor2_level = 0

        if self._enter_config_mode():
            self._enable_config_analog_sticks(enable_sticks)
            self._enable_config_rumble(enable_rumble)
            self._enable_config_analog_buttons(enable_pressure)
            if not self._exit_config_mode():
                print("PS2Controller: config exit error")
        else:
            print("PS2Controller: could not connect")

        self.update()  # to get initial button state

    def update(self):
        """Read the controller and return a list of PS2ButtonEvents.
        Must be called frequently or the controller disconnects.
        """
        start_t = time.monotonic()  # debugging
        self.data = self.read()
        self.last_dt = time.monotonic() - start_t

        if not _is_valid_reply(self.data):
            return None  # None means error like disconnect
        self._last_buttons = self._buttons
        self._buttons = self.data[4] << 8 | self.data[3]
        events = []
        for i in range(16):
            if self._last_buttons & (1 << i) != self._buttons & (1 << i):
                pressed = (self._buttons & (1 << i)) == 0
                released = not pressed
                events.append(PS2ButtonEvent(i, pressed, released, PS2Button.names[i]))
        return events

    def read(self):
        """Read from the controller. Must be called frequently. Called by update()."""
        self._attention()
        if self.enable_rumble:
            pollr = list(_poll_rumble)
            pollr[3] = self.motor1_level
            pollr[4] = self.motor2_level
            inbuf = self._autoshift(pollr)
        else:
            inbuf = self._autoshift(_poll)
        self._no_attention()

        if _is_valid_reply(inbuf):
            if _is_config_reply(inbuf):
                self._exit_config_mode()

        return inbuf

    def connected(self):
        """Returns True if controller was connected as of last update()"""
        return _is_valid_reply(self.data)

    def buttons(self):
        """Return a 16-bit bitfield of the state of all buttons"""
        return self._buttons

    def button(self, button_id):
        """Return True if button is currently pressed

        :param int button_id: 0-15 id number from PS2ButtonEvent.id or PS2Button.*
        """
        return (self._buttons & (1 << button_id)) == 0

    def analog_button(self, button_id):
        """Return analog pressure (0-255) value for button,
        if in pressure mode, otherwise -1.

        :param int button_id 0-15 id number PS2ButtonEvent.id or PS2Button.*
        """
        if len(self.data) < 21:
            return -1
        return self.data[PS2Button.button_to_analog_id[button_id]]

    def analog_right(self):
        """Return (x,y) tuple (0-255,0-255) of the right analog stick, if present."""
        if len(self.data) < 6:
            return (-1, -1)
        return (self.data[5], self.data[6])

    def analog_left(self):
        """Return (x,y) tuple (0-255,0-255) of the left analog stick, if present."""
        if len(self.data) < 6:
            return (-1, -1)
        return (self.data[7], self.data[8])

    def _attention(self):
        """Select joystick for reading/writing"""
        self.att_pin.value = False  # active low CS pin
        _delay_micros(_ATTN_DELAY_MICROS)

    def _no_attention(self):
        """Deselect joystick for reading/writing"""
        self.cmd_pin.value = True
        self.clk_pin.value = True  # idle state
        self.att_pin.value = True
        _delay_micros(_ATTN_DELAY_MICROS)

    def _shift_inout_byte(self, byte_out):
        """Bit-bang out a single byte on cmd_pin, while reading in a single byte on dat_pin"""
        byte_in = 0
        # clock is held high until a byte is to be sent
        for i in range(8):
            self.cmd_pin.value = (byte_out & (1 << i)) != 0  # send OUT data on cmd pin
            self.clk_pin.value = False  # clock LOW
            _delay_micros(_HOLD_TIME_MICROS)
            if self.dat_pin.value:  # read IN data on dat pin
                byte_in |= 1 << i
            self.clk_pin.value = True  # clock HIGH
            _delay_micros(_HOLD_TIME_MICROS)
        return byte_in

    def _shift_inout_buf(self, bytes_out):
        """
        Send out a buffer of bytes on cmd_pin,
        while reading in a same-sized buffer on dat_pin
        """
        inbuf = [0] * len(bytes_out)
        for i, bout in enumerate(bytes_out):
            inbuf[i] = self._shift_inout_byte(bout)
            _delay_micros(_BYTE_DELAY_MICROS)
        return inbuf

    def _autoshift(self, cmd_out):
        """
        Send out a command buffer to the controller,
        while also reading in a variable-length response buffer
        Returns the exact size buffer returned by the controller,
        or the invalid '0xff' 3-byte initial read buffer
        """
        cmdlen = len(cmd_out)
        if cmdlen < 3:
            return None  # wat

        # all commands have at least 3 bytes, so shift those out first
        inbufA = self._shift_inout_buf(cmd_out[0:3])

        if _is_valid_reply(inbufA):
            reply_len = _get_reply_length(inbufA)
            # print("\t\t\t\tvalid len:", reply_len, "iscfg:",_is_config_reply(inbufA))
            inbufB = []  # hack
            if cmdlen > 3:  # shift out rest of command
                inbufB = self._shift_inout_buf(cmd_out[3:])

            num_left = reply_len - cmdlen + 3
            # print("\t\t numleft:",num_left)
            if num_left == 0:
                return inbufA + inbufB

            # else pad output to get remaining input
            inbufC = self._shift_inout_buf([0x5A] * num_left)
            return inbufA + inbufB + inbufC

        return inbufA  # on error

    def _enter_config_mode(self):
        """Enter config mode to enable changing analog/digital/pressure modes"""
        return self._change_config_mode(_enter_config)

    def _exit_config_mode(self):
        """Exit config mode to go back to regular polling mode"""
        return self._change_config_mode(_exit_config)

    def _change_config_mode(self, outbuf):
        start_t = time.monotonic()
        while (time.monotonic() - start_t) < _COMMAND_TIMEOUT_SECS:
            self._attention()
            inbuf = self._autoshift(outbuf)
            self._no_attention()

            if _is_valid_reply(inbuf) and _is_config_reply(inbuf):
                time.sleep(_MODE_SWITCH_DELAY_SECS)
                return True
        # print("PS2Controller: change_config_mode timeout!!!")
        return False

    def _try_enable_mode(self, outbuf):
        """
        Attempt to enable a controller mode. Returns True if no timeout.
        If controller does not support mode, this function does NOT verify it
        """
        good_reply_count = 0
        start_t = time.monotonic()
        while (time.monotonic() - start_t) < _COMMAND_TIMEOUT_SECS:
            self._attention()
            inbuf = self._autoshift(outbuf)
            self._no_attention()

            # "We can't know if we have successfully enabled analog mode until
            # we get out of config mode, so let's just be happy if we get a few
            # consecutive valid replies"
            if inbuf is not None:
                good_reply_count += 1
                if good_reply_count == 3:
                    time.sleep(_MODE_SWITCH_DELAY_SECS)
                    return True
        return False

    def _enable_config_analog_sticks(self, enable=True, locked=True):
        """Attempt to enable analog joysticks"""
        outbuf = list(_set_mode)
        outbuf[3] = 1 * enable
        outbuf[4] = 1 * locked
        return self._try_enable_mode(outbuf)

    def _enable_config_rumble(self, enable=True):
        """Attempt to enable rumble motors"""
        outbuf = list(_enable_rumble)
        outbuf[3] = 0xFF * enable  # convert True/False to 0xFF/0x00
        outbuf[4] = 0xFF * enable
        return self._try_enable_mode(outbuf)

    def _enable_config_analog_buttons(self, enable=True):
        """Attempt to enable analog (pressure) buttons"""
        outbuf = list(_set_pressures)
        if not enable:
            outbuf[3:5] = (0, 0, 0)
        return self._try_enable_mode(outbuf)
