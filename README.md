# r00tz badge code for DEF CON 27

## Pre-requisites:
- Device Driver - https://www.silabs.com/products/development-tools/software/usb-to-uart-bridge-vcp-drivers
- Python 3
- `pip install esptool pyserial mpfshell`
- a badge or two!


## Pushing code to your boards
First, connect the boards to your computer via USB. If you connect them one at a time, the `flash`
script can do most of the work for you:
```bash
$ ./flash
esptool.py v2.7
Serial port /dev/cu.SLAB_USBtoUART
Connecting........_
Detecting chip type... ESP32
Chip is ESP32D0WDQ6 (revision 1)
Features: WiFi, BT, Dual Core, Coding Scheme None
Crystal is 40MHz
MAC: 30:ae:a4:1b:96:20
Uploading stub...
Running stub...
Stub running...
Erasing flash (this may take a while)...
Chip erase completed successfully in 0.6s
Hard resetting via RTS pin...
esptool.py v2.7
Serial port /dev/cu.SLAB_USBtoUART
Connecting........__
Chip is ESP32D0WDQ6 (revision 1)
Features: WiFi, BT, Dual Core, Coding Scheme None
Crystal is 40MHz
MAC: 30:ae:a4:1b:96:20
Uploading stub...
Running stub...
Stub running...
Changing baud rate to 921600
Changed.
Configuring flash size...
Auto-detected Flash size: 4MB
Flash params set to 0x022f
Compressed 18208 bytes to 11559...
Wrote 18208 bytes (11559 compressed) at 0x00001000 in 0.2 seconds (effective 931.5 kbit/s)...
Hash of data verified.
Compressed 1166384 bytes to 751919...
Wrote 1166384 bytes (751919 compressed) at 0x00010000 in 10.3 seconds (effective 903.5 kbit/s)...
Hash of data verified.
Compressed 3072 bytes to 142...
Wrote 3072 bytes (142 compressed) at 0x00008000 in 0.0 seconds (effective 4390.3 kbit/s)...
Hash of data verified.

Leaving...
Hard resetting via RTS pin...
Connected to BADGE.TEAM ESP32
Pushing: src/__init__.py -> /lib/r00tz27/__init__.py
Pushing: src/songs.py -> /lib/r00tz27/songs.py
Pushing: src/rtttl.py -> /lib/r00tz27/rtttl.py
Pushing: src/main.py -> /lib/r00tz27/main.py
Pushing: src/states.py -> /lib/r00tz27/states.py
Pushing: src/devices.py -> /lib/r00tz27/devices.py
Entering REPL. Usual shortcuts:
 Ctrl+D - soft reset board
 Ctrl+Q - push latest to board and restart REPL
 Ctrl+Q+C - quit this program
Ignore the following message:

*** Exit REPL with Ctrl+] ***>

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

Thanks to [badge.team](https://github.com/badgeteam/ESP32-platform-firmware) for help with the firmware.
