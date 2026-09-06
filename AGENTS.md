# AGENTS.md — mbot2-mcp

Stdio MCP server (opencode-spawned) driving mBot2/CyberPi over serial. One line out / one line back at 115200 baud to `cyberpi/mbot2_bridge.py` running on the robot.

## Layout

- `src/mbot2_mcp/server.py` — 12 MCP tools (`list_robots ping drive stop forward ultrasonic line_sensor gyro battery set_led beep show_text`)
- `src/mbot2_mcp/transport.py` — `SerialTransport` + `MockTransport`
- `src/mbot2_mcp/config.py` — env: `MBOT2_PORT`, `MBOT2_BOTS="A=/dev/ttyUSB0,B=/dev/ttyUSB1"`, `MBOT2_MOCK=1`
- `cyberpi/mbot2_bridge.py` — MicroPython `main.py` for the CyberPi (uploaded via mBlock, not deployed from here)
- `docs/01–04` — setup/upload/opencode-calibration/troubleshooting log (consult before re-diagnosing serial issues)

## Hard constraints (violations broke this repo before)

- **Keep `mcp>=1,<2` in `pyproject.toml`.** mcp 2.x renamed `FastMCP` → `MCPServer`; `from mcp.server.fastmcp import FastMCP` fails on v2. Upgrading means migrating `server.py`.
- **Never suggest Arduino flashing for the CyberPi** — it wipes CyberOS. The bridge is a MicroPython `main.py` upload, which coexists with CyberOS.
- **The `0xFF 0x55` frame protocol is mBot v1, not mBot2.** Do not implement it here; this repo's protocol is the plain-text lines in `02-bridge-upload.md`.
- **No test suite exists.** Verify with the two commands below, not pytest.
- **`cyberpi/mbot2_bridge.py`'s entry point must stay registered via
  `@event.start` (from `import event`), never a bare
  `if __name__ == "__main__"` block.** Confirmed 2026-09-06: a
  non-`@event.start` entry point boots the CyberPi to the Makeblock logo
  then hangs/goes dark, requiring a firmware reinstall — reproduced twice,
  with unrelated code (the full bridge script and a trivial one-liner),
  independent of what the code does. Device APIs must also stay top-level
  imports (`import mbot2`, `import mbuild`), not `cyberpi.mbot2` /
  `cyberpi.ultrasonic2` attribute access — see
  `history/2026-09-06_mlink-fix-and-bridge-upload-brick.md` for the full
  incident. Re-test any structural change with a small marker-bearing
  snippet before trusting the full bridge again.

## Commands

```bash
pip install -e .
MBOT2_MOCK=1 python3 -c "
import asyncio; from mbot2_mcp.server import mcp
asyncio.run(mcp.list_tools())  # expect 12 tools
"
sg dialout -c "python3 -c \"
from mbot2_mcp.transport import SerialTransport
import time; t = SerialTransport('/dev/ttyUSB0'); time.sleep(1.5)
print(t.command('PING'))  # expect OK PONG (bridge uploaded + bot powered on)
\""
```

## Serial gotchas (all observed 2026-09-06, details in `docs/04-troubleshooting.md`)

- `Permission denied` on `/dev/ttyUSB0` → user missing `dialout` group. Fix membership, never `sudo python` (root lacks the user-local install → `ModuleNotFoundError`).
- Port opens but `PING` times out and raw reads are silent → bridge not uploaded yet OR bot power switch OFF (CH340 enumerates even when powered off).
- Only one process may hold the port: mBlock browser tab / mLink session must be closed before the MCP (or the probe above) can open it.
- Uncalibrated: motor polarity sign in the bridge `DRIVE` handler (`drive_power(l, -r)`) and `quad_rgb_sensor index=1` are assumptions awaiting hardware confirmation — see `docs/03-opencode-mcp.md` §4.
- mLink `.deb` must be downloaded **in a browser** from `https://s.mblock.cc/download/mlink-deb`; `curl` returns a JS landing page, not the package.
