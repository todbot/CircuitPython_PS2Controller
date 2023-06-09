# SPDX-FileCopyrightText: Copyright (c) 2023 Tod Kurt
#
# SPDX-License-Identifier: Unlicense
# fmt: off

import board
from ps2controller import PS2Controller

# one way to wire this up, for example on a Pico
ps2 = PS2Controller(dat=board.GP2, cmd=board.GP3, att=board.GP4, clk=board.GP5,
                    enable_pressure=True)

print("be prepared to be spammed, this is raw data from the controller")
while True:
    events = ps2.update()
    print("dt:%2d" % int(ps2.last_dt*1000),
          "data:",' '.join("%2x" % v for v in ps2.data),
          "events:",len(events) if events is not None else 'None')
