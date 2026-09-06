# Bridge upload — CyberPi via Chrome + mLink

Prerequisites: `01-linux-setup.md` done (mLink running, user in `dialout`,
bot port known — here `/dev/ttyUSB0`).

## 1. Power the bot ON

Flip the **side power switch on the mBot2 ON**. The ultrasonic + line-follower
LEDs must light up. Verified symptom 2026-09-06: with power off, the CH340 USB
chip still enumerates `/dev/ttyUSB0` but the port is **stone silent** — no boot
text, no REPL (`Ctrl-C`/`Ctrl-D` get no response), `PING` times out. If the port
is silent, check power first.

## 2. Connect in Chrome

1. Chrome (or Edge) → <https://python.mblock.cc/> (preferred for a `.py` paste)
   or <https://ide.mblock.cc/>.
2. Add device **CyberPi** → **Connect** → pick the USB serial port
   (`/dev/ttyUSB0`) when the browser/mLink prompts.
3. Switch the editor to **Upload mode** (NOT Live mode).

## 3. Upload the bridge

1. Open `cyberpi/mbot2_bridge.py` from this repo, paste the whole file as `main.py`.
2. Press **Upload**, wait for success.
3. Expected: CyberPi flashes blue LEDs briefly, then prints
   `OK READY mbot2-bridge v0.1.0` on serial at 115200 baud.

Why this file: stock CyberOS speaks only mBlock's proprietary Live protocol
over serial (undocumented). The bridge is a plain MicroPython `main.py` that
listens for one-line text commands (`DRIVE 50 50`, `ULTRA?`, …) and calls the
documented `cyberpi.*` API. A MicroPython upload **does not wipe CyberOS**
(unlike Arduino flashing, which does) — you can overwrite it from mBlock anytime.

Protocol reference (115200 baud, `\n`-terminated, one line back):

| PC → CyberPi            | ← reply              |
|-------------------------|----------------------|
| `PING`                  | `OK PONG`            |
| `DRIVE <l> <r>` (−100..100) | `OK`             |
| `STOP`                  | `OK`                 |
| `FORWARD <spd> <secs>`  | `OK`                 |
| `LED <r> <g> <b> <id>`  | `OK`                 |
| `BEEP <freq> <ms>`      | `OK`                 |
| `TEXT <msg>`            | `OK`                 |
| `ULTRA?`                | `DIST <cm>`          |
| `LINE?`                 | `LINE <b0> <b1> <b2> <b3>` |
| `GYRO?`                 | `GYRO <roll> <pitch> <yaw>` |
| `BAT?`                  | `BAT <pct>`          |

## 4. Release the port, verify from this repo

**Close the browser tab** (or Disconnect the device) — only one process can hold
the serial port. Then:

```bash
sg dialout -c "python3 -c \"
from mbot2_mcp.transport import SerialTransport
import time
t = SerialTransport('/dev/ttyUSB0')
time.sleep(1.5)
print('PING ->', t.command('PING'))
print('BAT  ->', t.command('BAT?'))
\""
# PING -> OK PONG
# BAT  -> BAT 87
```

If `OK PONG` arrives, the chain
`opencode → mbot2-mcp → /dev/ttyUSB0 → bridge → mBot2` is live.
→ `03-opencode-mcp.md` for wiring into opencode + calibration checklist.
