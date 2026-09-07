# mbot2-mcp — CyberPi welcome greeter

`cyberpi/welcome_greeter.py` is a standalone MicroPython program for the
CyberPi (mBot2's brain board). It plays a greeting once at boot — no PC,
no serial link, no MCP server involved:

1. **Speak & greet** (~2s) — cyan LED ring, "Hello!" on screen, plays the
   built-in `"hello"` audio preset (`cyberpi.audio.play_until`).
2. **Dance** (~6-8s) — four moves (turn/forward/backward), each paired
   with an LED color and a drum hit, run twice through, ending in the
   built-in `rainbow` LED animation.
3. **End text** (~2s) — LEDs off, screen shows "Welcome to class!".

Confirmed working on real hardware 2026-09-06. The repo name is a
holdover: it started as a PC-side MCP server that remote-controlled an
mBot2 over serial (opencode → tools → USB/serial → a bridge script on
the CyberPi). That server, its bridge script, and everything PC-side
have been removed — this is now a pure on-device program. See
`docs/superpowers/specs/2026-09-06-cyberpi-welcome-greeter-design.md`
for the design behind the pivot.

## Uploading it

Get `cyberpi/welcome_greeter.py` onto the board as `main.py`:

- **Manually**: <https://ide.mblock.cc/> or <https://python.mblock.cc/> →
  connect the CyberPi (USB via mLink, or Bluetooth — see below) →
  switch to Upload mode → paste the file's contents in as `main.py` →
  Upload.
- **Via the `upload-cyberpi` skill**: drives the same mBlock web IDE
  through browser automation, including a byte-for-byte content check
  before uploading. See `.claude/skills/upload-cyberpi/SKILL.md`.

A MicroPython upload does **not** wipe CyberOS (unlike flashing Arduino
firmware, which does) — re-upload anytime.

**Hard constraint:** the entry point must stay registered via
`@event.start` (from `import event`), never a bare
`if __name__ == "__main__"` block. A non-`@event.start` entry point
bricked this board twice this session (boots to the Makeblock logo, then
hangs) — see `history/2026-09-06_mlink-fix-and-bridge-upload-brick.md`.

## Docs (knowledge captured 2026-09-06, don't lose it)

- `docs/01-linux-setup.md` — mLink driver download, install, `dialout`
  group fix (getting a browser talking to the board over USB)
- `docs/02-bridge-upload.md` — power on, connect + upload in Chrome;
  written for the old serial bridge, but the connect/Upload-mode steps
  apply to uploading any `.py` file, including this one
- `docs/03-opencode-mcp.md` — opencode wiring for the now-removed MCP
  server; stale, kept for historical/protocol reference only
- `docs/04-troubleshooting.md` — every connection/upload failure seen so
  far and its fix
- `docs/05-cyberpi-mbot2-api-reference.md` — confirmed `cyberpi`/`mbot2`/
  `mbuild` API calls (LED, audio, display, movement, sensors), sourced
  from a community MicroPython example set; use this instead of guessing
  signatures
- `docs/06-usb-upload-protocol.md` — the mBlock USB upload framing
  (`F3`/`F4`, checksum, sequence), decoded 2026-09-08; backing
  `scripts/mbot_upload.py`, which uploads any `size % 80 == 4` file over
  raw serial with no browser/mLink:
  `sg dialout -c "python3 scripts/mbot_upload.py cyberpi/<file>.py"`
- `history/2026-09-08_browser-free-upload.md` — how the direct
  programming path was re-iterated (USB stdin dead, UART alive,
  framing cracked, red LED + hi/cheers demos)

## USB vs. Bluetooth

Either connection works for uploading via mBlock's browser IDE. One
wrinkle worth knowing: the CyberPi's Bluetooth is **BLE-only** (GATT
characteristic `0000ffe1`, an HM-10-style BLE-UART module) — not classic
Bluetooth SPP. It never shows up as a `/dev/rfcomm0`-style serial port;
mBlock's browser reaches it over Web Bluetooth instead. That distinction
mattered a lot when this repo still had a `pyserial`-based transport
(which can't talk to BLE at all) — it's now just background context for
whoever connects a board. Full investigation:
`history/2026-09-06_mlink-fix-and-bridge-upload-brick.md` Part 7.
