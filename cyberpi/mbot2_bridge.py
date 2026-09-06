# mBot2 bridge for CyberPi (MicroPython) — upload ONCE via mBlock, then leave it.
#
# What it does: listens on USB serial (and Bluetooth-serial when paired) for
# one-line text commands from the MCP server, drives the mBot2, replies one line.
#
# Protocol (PC -> CyberPi, each line ends with \n):
#   PING                 -> OK PONG
#   DRIVE <l> <r>        -> OK            (l/r -100..100)
#   STOP                 -> OK
#   FORWARD <spd> <secs> -> OK            (spd 0..100, secs 0 = keep going)
#   LED <r> <g> <b> <id> -> OK            (id all | 1..5)
#   BEEP <freq> <ms>     -> OK
#   TEXT <msg>           -> OK            (shows on CyberPi screen)
#   ULTRA?               -> DIST <cm>
#   LINE?                -> LINE <b0> <b1> <b2> <b3>
#   GYRO?                -> GYRO <roll> <pitch> <yaw>
#   BAT?                 -> BAT <pct>
#
# Upload: mBlock 5 (or Python editor at python.mblock.cc) -> connect CyberPi
# via USB -> switch to Upload mode -> paste this file as main.py -> Upload/Run.
# MicroPython upload does NOT wipe CyberOS (Arduino would — don't use that).
# After upload, CLOSE mBlock (it holds the serial port), then the MCP owns it.

import sys
import time

import cyberpi as cpi

# mBot2 extension lives under cyberpi.mbot2 on recent firmware.
mbot2 = getattr(cpi, "mbot2", None)


def _reply(s):
    sys.stdout.write(str(s) + "\n")


def _clamp(v, lo, hi):
    try:
        v = int(float(v))
    except Exception:
        v = 0
    return max(lo, min(hi, v))


def handle(line):
    parts = line.strip().split()
    if not parts:
        return
    cmd = parts[0].upper()
    arg = parts[1:]

    try:
        if cmd == "PING":
            _reply("OK PONG")

        elif cmd == "DRIVE":
            l = _clamp(arg[0] if len(arg) > 0 else 0, -100, 100)
            r = _clamp(arg[1] if len(arg) > 1 else 0, -100, 100)
            if mbot2 is not None:
                # drive_power(left, right): positive = forward (verify on YOUR bot, §3)
                mbot2.drive_power(l, -r)
            _reply("OK")

        elif cmd == "STOP":
            if mbot2 is not None:
                try:
                    mbot2.EM_stop(port="all")
                except Exception:
                    mbot2.drive_power(0, 0)
            _reply("OK")

        elif cmd == "FORWARD":
            spd = _clamp(arg[0] if len(arg) > 0 else 50, 0, 100)
            secs = float(arg[1]) if len(arg) > 1 else 0
            if mbot2 is not None:
                if secs > 0:
                    mbot2.forward(speed=spd, run_time=secs)
                else:
                    mbot2.forward(speed=spd)
            _reply("OK")

        elif cmd == "LED":
            r = _clamp(arg[0] if len(arg) > 0 else 0, 0, 255)
            g = _clamp(arg[1] if len(arg) > 1 else 0, 0, 255)
            b = _clamp(arg[2] if len(arg) > 2 else 255, 0, 255)
            led_id = arg[3] if len(arg) > 3 else "all"
            try:
                if str(led_id).lower() == "all":
                    cpi.led.on(r, g, b)
                else:
                    cpi.led.on(r, g, b, id=int(led_id))
            except Exception:
                cpi.led.on(r, g, b)
            _reply("OK")

        elif cmd == "BEEP":
            freq = int(float(arg[0])) if len(arg) > 0 else 880
            ms = int(float(arg[1])) if len(arg) > 1 else 200
            try:
                cpi.audio.play_tone(freq, ms / 1000.0)
            except Exception:
                try:
                    cpi.audio.play("beep")
                except Exception:
                    pass
            _reply("OK")

        elif cmd == "TEXT":
            msg = line.strip()[5:].strip()[:48] or "hi"
            try:
                cpi.display.show_label(msg, 16, "center")
            except Exception:
                try:
                    cpi.console.println(msg)
                except Exception:
                    pass
            _reply("OK")

        elif cmd == "ULTRA?":
            try:
                d = cpi.ultrasonic2.get(index=1)
            except Exception:
                try:
                    d = cpi.ultrasonic.get()
                except Exception:
                    d = -1
            _reply("DIST %s" % (d,))

        elif cmd == "LINE?":
            try:
                # quad RGB sensor in line-follower mode; returns 4 binary states
                vals = cpi.quad_rgb_sensor.get_line_sta(index=1)
                _reply("LINE %d %d %d %d" % tuple(int(v) for v in vals[:4]))
            except Exception:
                _reply("LINE 0 0 0 0")

        elif cmd == "GYRO?":
            try:
                roll = cpi.get_roll()
                pitch = cpi.get_pitch()
                yaw = cpi.get_yaw()
            except Exception:
                roll = pitch = yaw = 0
            _reply("GYRO %s %s %s" % (roll, pitch, yaw))

        elif cmd == "BAT?":
            try:
                pct = cpi.get_battery()
            except Exception:
                pct = -1
            _reply("BAT %s" % (pct,))

        else:
            _reply("ERR unknown:%s" % cmd)
    except Exception as e:
        _reply("ERR %s" % (e,))


def main():
    # Small boot blip so you know the bridge is running (blue LEDs).
    try:
        cpi.led.on(0, 0, 255)
        time.sleep(0.3)
        cpi.led.off()
    except Exception:
        pass
    _reply("OK READY mbot2-bridge v0.1.0")
    buf = ""
    while True:
        # Blocking-ish stdin read: MicroPython gives us bytes or str depending on build.
        try:
            ch = sys.stdin.read(1)
        except Exception:
            time.sleep(0.05)
            continue
        if not ch:
            time.sleep(0.02)
            continue
        if isinstance(ch, bytes):
            try:
                ch = ch.decode()
            except Exception:
                continue
        if ch in ("\n", "\r"):
            if buf.strip():
                handle(buf)
                buf = ""
        else:
            buf += ch
            if len(buf) > 200:  # safety: drop overlong lines
                buf = ""


if __name__ == "__main__":
    main()
