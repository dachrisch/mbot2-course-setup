"""List serial ports. Unplug bot, run, plug in, run again — the new entry is yours."""
import sys

try:
    from serial.tools import list_ports
except ImportError:
    sys.exit("pyserial not installed: pip install -e /home/cda/dev/mbot2-mcp")

print("serial ports:")
for p in list_ports.comports():
    print(f"  {p.device:24} {p.description} [{p.vid:04x}:{p.pid:04x}]" if p.vid else f"  {p.device:24} {p.description}")
