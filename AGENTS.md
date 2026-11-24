# AGENTS.md — mbot2-mcp

CyberPi (mBot2's brain board) course setup: an on-device MicroPython greeter
in `cyberpi/`, plus a browser-free, upload-only MCP server in `src/cyberpi_mcp/`
that puts those files on the board over USB serial. The repo name is a holdover
from a removed live-control serial bridge; see `README.md`.

## Component guides

- [cyberpi/AGENTS.md](cyberpi/AGENTS.md) — on-device MicroPython programs:
  `@event.start`, top-level imports, marker heartbeats, upload as `main.py`.
- [src/AGENTS.md](src/AGENTS.md) — upload MCP server, framing protocol,
  environment config, mock mode.
- [tests/AGENTS.md](tests/AGENTS.md) — the hardware-free pytest suite.

## Repo-wide essentials

- `pyproject.toml` — package `cyberpi-upload-mcp`, Python >= 3.10, deps `mcp`
  and `pyserial`, console script `cyberpi-upload`, pytest `testpaths = ["tests"]`.
- `scripts/mbot_upload.py` — thin CLI over the protocol; `scripts/list_ports.py`
  — enumerate serial ports by unplug/plug diff; `opencode-mcp.example.json` —
  MCP wiring.
- `docs/05-cyberpi-mbot2-api-reference.md` — confirmed `cyberpi`/`mbot2`/
  `mbuild` calls; consult before guessing a signature. `docs/06-usb-upload-protocol.md`
  — framing; `docs/07-cyberpi-upload-mcp.md` — rollout. `docs/01-linux-setup.md`
  (mLink/USB setup) is still accurate; in `docs/04-troubleshooting.md` only the
  mLink/dialout/USB connectivity rows are current — rows about the deleted
  bridge/MCP package are stale, ignore them.
- `docs/02-bridge-upload.md`, `docs/03-opencode-mcp.md` — written for the
  deleted PC-side bridge; stale, but `02`'s connect/Upload-mode steps still
  apply to any `.py` upload.
- `.claude/skills/upload-cyberpi/SKILL.md` and
  `.opencode/skills/upload-cyberpi/SKILL.md` — browser-IDE upload fallback.
  Repo-specific reusable workflows belong in those skill dirs; don't invent
  new ones here.
- `history/2026-09-06_mlink-fix-and-bridge-upload-brick.md` — the incident
  behind the `@event.start` constraint; `history/2026-09-08_browser-free-upload.md`
  — how the browser-free path was built.

## Hard constraints (violations broke this repo before)

- **Never suggest Arduino flashing for the CyberPi** — it wipes CyberOS.
  A MicroPython `main.py` upload coexists with CyberOS.
- **On-device entry points must stay registered via `@event.start`.** Details
  and the failure mode are in [cyberpi/AGENTS.md](cyberpi/AGENTS.md).
- **No automated green light:** physical LED/screen confirmation (or a serial
  marker where readable) is the verdict. USB stdout is silent on this board, so
  markers are best-effort. Don't call an upload good until the user confirms.

## Verify and upload

```bash
python3 -m pytest tests/ -q      # 11 hardware-free tests; see tests/AGENTS.md
wc -c cyberpi/welcome_greeter.py # byte-length sanity check before an upload
```

Upload order of preference: MCP `upload` tool → CLI
(`sg dialout -c "python3 scripts/mbot_upload.py cyberpi/<file>.py"`) →
browser skill fallback. See [src/AGENTS.md](src/AGENTS.md) and
[cyberpi/AGENTS.md](cyberpi/AGENTS.md). Note the board currently runs
`cyberpi/red_test.py`; re-upload the greeter for the next demo.

## Serial gotchas (observed 2026-09-06; details in `docs/04-troubleshooting.md`)

- `Permission denied` on `/dev/ttyUSB0` → user missing `dialout`. Fix with
  `sudo usermod -aG dialout $USER`, then log out/in — needed by mLink itself,
  not by repo code.
- A device can show connected with the bot powered OFF (the CH340 enumerates
  regardless of power). If mBlock sees it but nothing responds, check the
  physical switch (sensor LEDs lit = powered).
- Only one process can hold the port: close other mBlock tabs / mLink sessions
  first (`Device or resource busy`).
- mLink's `.deb` must be downloaded **in a browser** from
  `https://s.mblock.cc/download/mlink-deb`; `curl` returns a JS landing page,
  not the package.
