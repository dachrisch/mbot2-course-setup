# cyberpi/uart_probe2.py
# Follow-up to uart_probe.py, which reported
#   "uart-fail:can't convert Pin to int"
# This firmware's machine.UART wants raw pin NUMBERS, not Pin objects.
# Tries both forms (int pins, then Pin objects) and reports each result
# over USB serial (print) + display/LED. No motors, no flash writes.
#
# IMPORTANT: entry point must stay registered via @event.start (see
# AGENTS.md / history/2026-09-06_mlink-fix-and-bridge-upload-brick.md) —
# a bare `if __name__ == "__main__"` block bricked this board twice.

import cyberpi
import event
import time

MARKER = "UART-PROBE2-7D4B2"


def _check():
    try:
        from machine import UART, Pin
    except Exception as e:
        return "no-machine:" + str(e)
    parts = ["machine-ok"]
    try:
        import ujson
        parts.append("ujson-ok")
    except Exception:
        parts.append("no-ujson")
    for label, tx, rx in (("int", 32, 25), ("pinobj", Pin(32), Pin(25))):
        try:
            u = UART(2, baudrate=115200, tx=tx, rx=rx,
                     bits=8, parity=None, stop=1)
            parts.append("uart-" + label + "-ok")
            try:
                u.write(b'{"evt":"hello"}\n')
                parts.append("write-" + label + "-ok")
            except Exception as e:
                parts.append("write-" + label + "-fail:" + str(e))
        except Exception as e:
            parts.append("uart-" + label + "-fail:" + str(e))
    return " ".join(parts)


@event.start
def on_start():
    cyberpi.led.on(0, 0, 255, id='all')
    cyberpi.display.clear()
    cyberpi.display.show_label("UART probe2", 16, 0, 20, 0)
    status = _check()
    print(MARKER + " boot " + status)
    if "uart-int-ok" in status or "uart-pinobj-ok" in status:
        cyberpi.led.on(0, 255, 0, id='all')
    else:
        cyberpi.led.on(255, 0, 0, id='all')
    while True:
        print(MARKER + " status " + status)
        time.sleep(2)
