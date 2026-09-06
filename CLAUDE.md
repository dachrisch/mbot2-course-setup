# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Stdio MCP server (opencode-spawned) that drives an mBot2/CyberPi robot over
serial. One line out / one line back at 115200 baud to `cyberpi/mbot2_bridge.py`
running on the robot itself.

```
opencode
  │ MCP (stdio)
  ▼
mbot2-mcp  (this repo: drive/stop/ultrasonic/line/gyro/led/beep)
  │ 1 line out / 1 line back, 115200 baud
  ▼
USB serial  ──or──  Bluetooth-serial (same serial port abstraction)
  ▼
CyberPi running mbot2_bridge.py  →  mBot2 chassis
```

No MQTT. No flashing of CyberOS — the bridge is a MicroPython `main.py` upload
(via mBlock), which coexists with CyberOS, unlike Arduino flashing which wipes it.

## Layout

- `src/mbot2_mcp/server.py` — the 12 MCP tools: `list_robots ping drive stop
  forward ultrasonic line_sensor gyro battery set_led beep show_text`
- `src/mbot2_mcp/transport.py` — `SerialTransport` (real serial) + `MockTransport`
  (deterministic fake robot), keyed per-robot-name in a module-level cache
- `src/mbot2_mcp/config.py` — resolves robot name → port from env
  (`MBOT2_PORT`, `MBOT2_BOTS`, `MBOT2_MOCK`)
- `cyberpi/mbot2_bridge.py` — MicroPython `main.py` that runs *on* the CyberPi.
  Uploaded via mBlock, not deployed from this repo. Defines the line protocol
  (`PING`, `DRIVE <l> <r>`, `STOP`, `FORWARD <spd> <secs>`, `LED <r> <g> <b>
  <id>`, `BEEP <freq> <ms>`, `TEXT <msg>`, `ULTRA?`, `LINE?`, `GYRO?`, `BAT?`)
- `scripts/list_ports.py` — enumerate serial ports (unplug/plug-in diffing to
  find a bot's device path)
- `docs/01–04` — setup/upload/opencode-calibration/troubleshooting log; consult
  before re-diagnosing serial issues, don't rediscover them from scratch

## Commands

Install:
```bash
pip install -e .
```

Verify the server loads and exposes all tools (no pytest suite exists — this
and the PING check below are the verification path):
```bash
MBOT2_MOCK=1 python3 -c "
import asyncio; from mbot2_mcp.server import mcp
asyncio.run(mcp.list_tools())  # expect 12 tools
"
```

Run against real hardware (needs `dialout` group membership, see below):
```bash
sg dialout -c "python3 -c \"
from mbot2_mcp.transport import SerialTransport
import time; t = SerialTransport('/dev/ttyUSB0'); time.sleep(1.5)
print(t.command('PING'))  # expect OK PONG (bridge uploaded + bot powered on)
\""
```

Run the server standalone in mock mode:
```bash
MBOT2_MOCK=1 python -m mbot2_mcp.server
```

Find a bot's serial port (run once unplugged, once plugged in, diff):
```bash
python scripts/list_ports.py
```

## Configuration (env vars, see `config.py`)

- `MBOT2_MOCK=1` — no hardware; deterministic fake responses (`DIST 42.0`,
  `LINE 0 1 1 0`, etc.)
- `MBOT2_PORT=/dev/ttyUSB0` — single bot
- `MBOT2_BOTS="A=/dev/ttyUSB0,B=/dev/ttyUSB1"` — course fleet, multiple bots
  addressed by name from the `robot` tool argument
- No port configured at all → falls back to mock so opencode still starts

## Hard constraints (violations broke this repo before)

- **Keep `mcp>=1,<2` in `pyproject.toml`.** mcp 2.x renamed `FastMCP` →
  `MCPServer`; `from mcp.server.fastmcp import FastMCP` fails on v2. Upgrading
  means migrating `server.py`.
- **Never suggest Arduino flashing for the CyberPi** — it wipes CyberOS. The
  bridge is a MicroPython `main.py` upload, which coexists with CyberOS.
- **The `0xFF 0x55` frame protocol is mBot v1 (Arduino), not mBot2.** Do not
  implement it here; this repo's protocol is the plain-text lines defined in
  `cyberpi/mbot2_bridge.py` and `docs/02-bridge-upload.md`.
- **No test suite exists.** Verify with the two commands above, not pytest.

## Serial gotchas (details in `docs/04-troubleshooting.md`)

- `Permission denied` on `/dev/ttyUSB0` → user missing `dialout` group. Fix
  group membership; never `sudo python` (root lacks the user-local install →
  `ModuleNotFoundError`).
- Port opens but `PING` times out and raw reads are silent → bridge not
  uploaded yet, OR bot power switch OFF (the CH340 USB chip enumerates even
  when the bot itself is powered off).
- Only one process may hold the serial port at a time: close the mBlock
  browser tab / mLink session before the MCP server (or the probe command
  above) can open it.
- Uncalibrated on new hardware: motor polarity sign in the bridge's `DRIVE`
  handler (`drive_power(l, -r)`) and `quad_rgb_sensor index=1` are assumptions
  awaiting confirmation on the actual chassis — see `docs/03-opencode-mcp.md` §4.
- mLink's `.deb` must be downloaded **in a browser** from
  `https://s.mblock.cc/download/mlink-deb`; `curl` returns a JS landing page,
  not the package.

## When real hardware is actually needed

Everything except calibration works in `MBOT2_MOCK=1` — no cable required for
day-to-day development. USB is only needed for: the one-time bridge upload via
mBlock (Bluetooth can't do this reliably), and calibrating motor
polarity/ultrasonic/gyro/battery scaling directly on the chassis. Bluetooth
pairing afterward just becomes another serial port name in `MBOT2_BOTS` — zero
code changes.
