# r00tz badge code for DEF CON 27

## Pre-requisites:
- Python 3
- `pip install pyserial mpfshell`
- two HUZZAH32 boards flashed with the badge.team firmware


## Pushing code to your boards
First, connect the boards to your computer via USB. Then see if they're detected:
```bash
$ python push.py
Usage: push.py [board port]

List of ports with attached boards:
- COM4 (Silicon Labs)
- COM3 (Silicon Labs)
```

COM ports can be different depending on your computer. On Windows: serial ports show up as COM1. MacOS: you might see /dev/cu.. On Linux: /dev/tty

Open two terminals (one for each board) and put in the ports you found.
```bash
$ python push.py COM3
Connected to BADGE.TEAM ESP32
Deleting: lib/r00tz27/__init__.py
Deleting: lib/r00tz27/devices.py
Deleting: lib/r00tz27/main.py
Deleting: lib/r00tz27/states.py
Pushing: src\devices.py -> /lib/r00tz27/devices.py
Pushing: src\main.py -> /lib/r00tz27/main.py
Pushing: src\states.py -> /lib/r00tz27/states.py
Pushing: src\__init__.py -> /lib/r00tz27/__init__.py
Entering REPL. Usual shortcuts:
...
>>> 
```

Now, you have a REPL in which you can type any Python code. Also, if everything went well, the contents of the `src/`  
directory were pushed to the board under `/lib/r00tz27/`.

Hit CTRL+D in the REPL to soft-reboot the board and see the output of the r00tz27 code:

```
>>>
ESP32: soft reboot
ets Jun  8 2016 00:22:57

rst:0xc (SW_CPU_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)
configsip: 0, SPIWP:0xee
clk_drv:0x00,q_drv:0x00,d_drv:0x00,cs0_drv:0x00,hd_drv:0x00,wp_drv:0x00
mode:DIO, clock div:1
load:0x3fff0018,len:4
load:0x3fff001c,len:3992
load:0x40078000,len:8100
load:0x40080000,len:5944
entry 0x400802b4



BADGE.TEAM
Starting app 'r00tz27'...
<...stdout from our code...>
```

CTRL+Q (to exit the REPL) will do a fresh push of code and start the REPL again.

To quit the `push.py` script entirely, hit CTRL+Q (to exit the REPL) and CTRL+C (to exit the script).
