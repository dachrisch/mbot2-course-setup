# cyberpi/serial_probe.py
# Minimal CLI-reachability probe: tests whether plain USB-serial
# stdout/stdin reaches MicroPython on this CyberPi firmware.
# Prints a unique marker heartbeat + echoes any received line.
# No flash writes, no motors, no audio. Safe to observe passively.
#
# IMPORTANT: entry point must stay registered via @event.start (see
# AGENTS.md / history/2026-09-06_mlink-fix-and-bridge-upload-brick.md) —
# a bare `if __name__ == "__main__"` block bricked this board twice.

import cyberpi
import event
import sys
import time

MARKER = "CLI-PROBE-7F3A9"


def _make_poll():
    try:
        try:
            import uselect as select
        except ImportError:
            import select
        poller = select.poll()
        poller.register(sys.stdin, select.POLLIN)
        return poller, select
    except Exception:
        return None, None


@event.start
def on_start():
    cyberpi.led.on(0, 255, 0, id='all')
    cyberpi.display.clear()
    cyberpi.display.show_label("CLI probe", 16, 0, 20, 0)
    print(MARKER + " boot")
    poller, select = _make_poll()
    if poller is None:
        print(MARKER + " no-poll stdin-unavailable")
    while True:
        print(MARKER + " heartbeat")
        if poller is not None:
            try:
                if poller.poll(0):
                    line = sys.stdin.readline()
                    if line:
                        print(MARKER + " echo:" + line.strip())
            except Exception:
                print(MARKER + " stdin-error")
                poller = None
        time.sleep(2)
