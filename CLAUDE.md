# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Standalone MicroPython program for the CyberPi (mBot2's brain board):
`cyberpi/welcome_greeter.py` plays a speak → dance → end-text greeting once
at boot. No PC, no serial link, no MCP server involved — everything runs
on-device.

## Layout

- `cyberpi/welcome_greeter.py` — the greeter itself: speak & greet → dance →
  end-text, run once from `@event.start`. Uploaded as the CyberPi's
  `main.py` via mBlock; not deployed from this repo.
- `docs/05-cyberpi-mbot2-api-reference.md` — confirmed `cyberpi`/`mbot2`/
  `mbuild` API calls (LED, audio, display, movement, sensors); consult
  before guessing a signature.
- `scripts/list_ports.py` — enumerate serial ports (unplug/plug-in diffing
  to find the board's device path).
- `docs/01-linux-setup.md` — mLink/USB setup; still accurate, consult
  before re-diagnosing.
- `docs/04-troubleshooting.md` — connection/upload failure log; the
  mLink/dialout/USB connectivity rows are still accurate, but several rows
  (the `PING`/bridge-upload row, the `ModuleNotFoundError: mcp...`/
  `mbot2_mcp` rows, the motor-polarity `DRIVE`-handler row, and the sensor
  `index=2` row) and the raw-port diagnosis snippet at the bottom are
  written for the now-deleted MCP/bridge package — ignore those.
- `docs/02-bridge-upload.md`, `docs/03-opencode-mcp.md` — written for the
  now-deleted PC-side bridge/MCP server; stale in places (rewriting them is
  out of scope here — see README), but `02`'s connect/Upload-mode steps
  still apply to uploading any `.py` file, including this one.
- `.claude/skills/upload-cyberpi/SKILL.md` — browser-automation procedure
  for uploading through the mBlock web IDE.
- `history/2026-09-06_mlink-fix-and-bridge-upload-brick.md` — the incident
  behind the `@event.start` constraint below.

## Commands

No install step and no test suite — this is a single MicroPython file
uploaded straight to the board.

```bash
wc -c cyberpi/welcome_greeter.py   # byte length; sanity-check the editor matches before uploading
```

Upload and verify via the `upload-cyberpi` skill
(`.claude/skills/upload-cyberpi/SKILL.md`, or
`/upload-cyberpi cyberpi/welcome_greeter.py`) — it drives the mBlock web
IDE, checks the editor content byte-for-byte against the local file before
uploading, and ends by asking the user to physically confirm the board's
boot behavior. There is no automated success signal; don't declare an
upload good until the user confirms.

Find the board's serial port (run once unplugged, once plugged in, diff) —
useful when connecting mBlock over USB:
```bash
python scripts/list_ports.py
```

## Hard constraints (violations broke this repo before)

- **Never suggest Arduino flashing for the CyberPi** — it wipes CyberOS.
  `welcome_greeter.py` is a MicroPython `main.py` upload, which coexists
  with CyberOS.
- **No test suite exists.** "Testing" means uploading via the
  `upload-cyberpi` skill and having the user physically confirm the
  board's behavior — see Commands above.
- **`cyberpi/welcome_greeter.py`'s entry point must stay registered via
  `@event.start` (from `import event`), never a bare
  `if __name__ == "__main__"` block.** Confirmed 2026-09-06: a
  non-`@event.start` entry point boots the CyberPi to the Makeblock logo
  then hangs/goes dark, requiring a firmware reinstall — reproduced twice,
  independent of what code was run (a full serial-bridge script and a
  trivial one-liner). Device APIs must also stay top-level imports
  (`import mbot2`, `import mbuild`), not `cyberpi.mbot2` /
  `cyberpi.ultrasonic2` attribute access — see
  `history/2026-09-06_mlink-fix-and-bridge-upload-brick.md` for the full
  incident. Re-test any structural change with a small marker-bearing
  snippet before trusting the full greeter again.

## Serial gotchas (all observed 2026-09-06, details in `docs/04-troubleshooting.md`)

- `Permission denied` on `/dev/ttyUSB0` → user missing the `dialout` group.
  Fix with `sudo usermod -aG dialout $USER`, then log out/in — needed by
  mLink itself, not any code in this repo.
- A device can show as connected even with the bot's power switch OFF —
  the CH340 USB-serial chip enumerates regardless of power state. If
  mBlock sees a device but nothing responds, check the physical switch
  (sensor LEDs lit = powered).
- Only one thing can hold the port at a time: close any other mBlock
  browser tab / mLink session before opening a new one
  (`Device or resource busy` if you don't).
- mLink's `.deb` must be downloaded **in a browser** from
  `https://s.mblock.cc/download/mlink-deb`; `curl` returns a JS landing
  page, not the package.

## When real hardware is actually needed

There's no mock mode and nothing to run off-device — the whole program
only makes sense executing on the CyberPi. A cable (or a Bluetooth
pairing) is needed for exactly two things: connecting mBlock's web IDE to
upload `welcome_greeter.py`, and letting the user physically watch the
board's boot behavior to confirm an upload is good. USB goes through
mLink (see Serial gotchas above); Bluetooth on this board is BLE-only
(GATT, not classic SPP) and connects via Web Bluetooth in the same mBlock
tab. Either way, verifying the greeting itself always requires a
powered-on board in front of the user — there's no way to check the
result from this repo alone.
