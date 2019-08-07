# This script is used to push the source files in src/ to the board under /lib/r00tz27/.
# If you run it without any arguments, it will print all the connected boards it detects.
# Run it with a single argument, a port (e.g. COM3 or /dev/ttyWhatever), to:
# 1) sync src/ with /lib/r00tz27/
# 2) open up a REPL (so you can hit CTRL+D/CMD+D and soft reboot the board to see any errors)
# 3) repeat the above if you quit the REPL
#
# Make sure you have installed the following python packages w/ pip:
# pyserial==3.4
# mpfshell==0.9.1

from mp.mpfshell import MpFileShell
from mp.mpfexp import RemoteIOError
from serial.tools import list_ports

from datetime import datetime
import os, sys

if len(sys.argv) != 2:
    print("Usage: push.py [board port]\n\nList of ports with attached boards:")

    ports = list(list_ports.grep("Silicon Labs"))
    if len(ports) == 0:
        ports = list(list_ports.grep("CP2104"))
        if len(ports) == 0:
            print("-> No boards seem to be attached to this computer.")
            sys.exit(1)

    for port in ports:
        print("- %s (%s)" % (port.device, port.manufacturer))

    sys.exit(1)


def rsync_src_directory_with_board(mpfs):
    mpfs.fe.cd("lib")
    try:
        mpfs.fe.cd("r00tz27")
    except RemoteIOError:
        # make directory if not exists
        mpfs.fe.md("r00tz27")
        mpfs.fe.cd("r00tz27")

    # delete all files in directory before pushing new ones
    for f in mpfs.fe.ls():
        print("Deleting: /lib/r00tz27/%s" % f)
        mpfs.fe.rm(f)

    files_to_transfer = [
        o for o in os.listdir("src") if os.path.isfile(os.path.join("src", o))
    ]
    for filename in files_to_transfer:
        local_file_path = os.path.join("src", filename)
        remote_file_path = "/lib/r00tz27/%s" % filename
        print("Pushing: %s -> %s" % (local_file_path, remote_file_path))
        mpfs.fe.put(local_file_path, remote_file_path)

    mpfs.do_exec("""machine.nvs_setstr("system", "default_app", "r00tz27")""")

    time_tuple = (datetime.now().timetuple())[0:5]
    mpfs.do_exec("machine.RTC().init(%s)" % str(time_tuple))


mpfs = MpFileShell(color=True, caching=False, reset=False)

port = sys.argv[1]
if port.startswith("/dev/"):
    port = port[len("/dev/"):]

while True:
    try:
        mpfs.do_open(port)

        try:
            rsync_src_directory_with_board(mpfs)

            print("Entering REPL. Usual shortcuts:")
            print(" Ctrl+D - soft reset board")
            print(" Ctrl+Q - push latest to board and restart REPL")
            print(" Ctrl+Q+C - quit this program")
            print("Ignore the following message: ")  # *** Exit REPL with Ctrl+Q ***
            mpfs.do_repl(None)
        finally:
            mpfs.do_close(None)
    except KeyboardInterrupt:
        break
    finally:
        mpfs.do_close(None)

print("Done.")
