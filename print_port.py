from serial.tools import list_ports


ports = list(list_ports.grep("CP2104"))
if len(ports) == 1:
    port = ports[0].device

print(port, end="")

