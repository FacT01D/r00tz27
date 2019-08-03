# This is the file that gets executed on boot. At some point,
#  you should have ran the following command on your board:
#    >>> machine.nvs_setstr("system", "default_app", "r00tz27")
#  then, the src/ folder here goes into /lib/r00tz27 on the board,
#  and r00tz27/__init__.py gets run on startup.

from .main import run

run()
