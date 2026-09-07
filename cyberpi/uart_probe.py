# cyberpi/uart_probe.py
# Community-path probe: can this CyberPi bring up machine.UART(2) on the
# gianpaj/makeblock bridge pins (TX=GPIO32, RX=GPIO25)?
# NOTE: their own PINOUT.md now marks these picks STALE (the bare CyberPi
# has no general-purpose pin header) — this probe only answers "does the
# peripheral init", which decides whether any wired-UART future exists.
# Reports over USB serial (print) + display/LED. No motors, no flash writes.
#
# IMPORTANT: entry point must stay registered via @event.start (see
# AGENTS.md / history/2026-09-06_mlink-fix-and-bridge-upload-brick.md) —
# a bare `if __name__ == "__main__"` block bricked this board twice.

import cyberpi
import event
import time

MARKER = "UART-PROBE-3C9E1"


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
    try:
        u = UART(2, baudrate=115200, tx=Pin(32), rx=Pin(25),
                 bits=8, parity=None, stop=1)
        parts.append("uart-ok")
        try:
            u.write(b'{"evt":"hello"}\n')
            parts.append("write-ok")
        except Exception as e:
            parts.append("write-fail:" + str(e))
    except Exception as e:
        parts.append("uart-fail:" + str(e))
    return " ".join(parts)


@event.start
def on_start():
    cyberpi.led.on(0, 0, 255, id='all')
    cyberpi.display.clear()
    cyberpi.display.show_label("UART probe", 16, 0, 20, 0)
    status = _check()
    print(MARKER + " boot " + status)
    if "uart-ok" in status and "uart-fail" not in status:
        cyberpi.led.on(0, 255, 0, id='all')
    else:
        cyberpi.led.on(255, 0, 0, id='all')
    while True:
        print(MARKER + " status " + status)
        time.sleep(2)
