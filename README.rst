Introduction
============


.. image:: https://readthedocs.org/projects/circuitpython-ps2controller/badge/?version=latest
    :target: https://circuitpython-ps2controller.readthedocs.io/
    :alt: Documentation Status

.. image:: https://img.shields.io/discord/327254708534116352.svg
    :target: https://adafru.it/discord
    :alt: Discord

.. image:: https://github.com/todbot/CircuitPython_PS2Controller/workflows/Build%20CI/badge.svg
    :target: https://github.com/todbot/CircuitPython_PS2Controller/actions
    :alt: Build Status

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
    :alt: Code Style: Black

CircuitPython library to read Sony PS2 or PS1 game controllers


Dependencies
=============
This driver depends on:

* `Adafruit CircuitPython <https://github.com/adafruit/circuitpython>`_

Please ensure all dependencies are available on the CircuitPython filesystem.
This is easily achieved by downloading
`the Adafruit library and driver bundle <https://circuitpython.org/libraries>`_
or individual libraries can be installed using
`circup <https://github.com/adafruit/circup>`_.

Installing from PyPI
=====================

On supported GNU/Linux systems like the Raspberry Pi, you can install the driver locally `from
PyPI <https://pypi.org/project/circuitpython-ps2controller/>`_.
To install for current user:

.. code-block:: shell

    pip3 install circuitpython-ps2controller

To install system-wide (this may be required in some cases):

.. code-block:: shell

    sudo pip3 install circuitpython-ps2controller

To install in a virtual environment in your current project:

.. code-block:: shell

    mkdir project-name && cd project-name
    python3 -m venv .venv
    source .env/bin/activate
    pip3 install circuitpython-ps2controller

Installing to a Connected CircuitPython Device with Circup
==========================================================

Make sure that you have ``circup`` installed in your Python environment.
Install it with the following command if necessary:

.. code-block:: shell

    pip3 install circup

With ``circup`` installed and your CircuitPython device connected use the
following command to install:

.. code-block:: shell

    circup install ps2controller

Or the following command to update an existing version:

.. code-block:: shell

    circup update

Usage Example
=============

.. code-block:: python

    import board
    from ps2controller import PS2Controller

    # one way to wire this up, for example on a Pico
    ps2 = PS2Controller(dat=board.GP2, cmd=board.GP3, att=board.GP4, clk=board.GP5)

    print("hi! Press buttons")
    while True:
        events = ps2.update()
        if events:
            print("events", events)
            print("sticks: L:", ps2.analog_left(), "R:", ps2.analog_right())

Wiring
======

Wiring to the PSX controller needs four GPIO pins.These can be any pins.
The wiring is:

* CLK pin - clock OUT to controller (blue wire)
* CMD pin - command data OUT to controller (orange wire)
* ATT pin - attention / chip select OUT to controller (yellow wire)
* DAT pin - data IN from controller (brown wire)
* GND pin - signal ground (black wire)
* VCC pin - +3.3V power (red wire)
* VCC2 pin - +7.5V power to rumble motors (optional)

Here's one way to wire that up on a Raspberry Pi Pico:

.. image:: https://raw.githubusercontent.com/todbot/CircuitPython_PS2Controller/main/docs/ps2controller_wiring.png

(Thanks to `Vanepp <https://forum.fritzing.org/u/vanepp/summary>`_ via `nandanhere/PiPyPS2 <https://github.com/nandanhere/PiPyPS2>`_ for Fritzing wiring diagram)


References
==========

This library is highly inspired by the `SukkoPera/PsxNewLib <https://github.com/SukkoPera/PsxNewLib>`_ library.
It currently has only been tested on a handful of PS1 and PS2 controllers,
but it should be easy to add any specialized controller tuning.

Other resources that have been helpful:

* https://store.curiousinventor.com/guides/PS2/
* https://gist.github.com/scanlime/5042071
* https://gamesx.com/wiki/doku.php?id=controls:playstation_controller
* https://github.com/SukkoPera/PsxNewLib
* https://github.com/nandanhere/PiPyPS2
* https://github.com/veroxzik/arduino-psx-controller
* https://github.com/madsci1016/Arduino-PS2X

Documentation
=============
API documentation for this library can be found on `Read the Docs <https://circuitpython-ps2controller.readthedocs.io/>`_.

For information on building library documentation, please check out
`this guide <https://learn.adafruit.com/creating-and-sharing-a-circuitpython-library/sharing-our-docs-on-readthedocs#sphinx-5-1>`_.

Contributing
============

Contributions are welcome! Please read our `Code of Conduct
<https://github.com/todbot/CircuitPython_PS2Controller/blob/HEAD/CODE_OF_CONDUCT.md>`_
before contributing to help this project stay welcoming.
