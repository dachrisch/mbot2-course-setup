# cyberpi-upload MCP

Upload-only MCP server for the CyberPi (mBot2 brain) over USB serial.
No browser, no mLink — it replays the upload framing decoded from a
captured mBlock IDE session (`docs/06-usb-upload-protocol.md`).

Proven on hardware 2026-09-19: first upload through the MCP itself
(`red_test.py`, all 19 frames acked first try, red LED confirmed).

## Install

```bash
pip install -e .          # from the repo root
python -m pytest tests/ -q
```

## Configure

opencode (`~/.config/opencode/opencode.json`, full example in
`opencode-mcp.example.json`):

```json
{ "mcp": { "cyberpi-upload": {
  "type": "local",
  "command": ["python", "-m", "cyberpi_mcp.server"],
  "enabled": true,
  "environment": { "CYBERPI_PORT": "/dev/ttyUSB0" }
} } }
```

Claude Code:

```bash
claude mcp add cyberpi-upload -- python -m cyberpi_mcp.server -e CYBERPI_PORT=$CYBERPI_PORT
```

Env knobs: `CYBERPI_PORT` (single board), `CYBERPI_BOTS="A=/dev/ttyUSB0,B=/dev/ttyUSB1"`
(fleet), `CYBERPI_MOCK=1` (hardware-free fakes).

## Tools

| Tool | What it does |
|---|---|
| `check_file(path)` | Pre-upload check: disk/wire size, `@event.start` guard (warns, doesn't block). |
| `list_local()` | `cyberpi/*.py` with size + guard status. |
| `upload(path, board, expect_marker)` | Full upload over USB serial. Close any mBlock tab first; power-cycle the bot if it doesn't boot within ~20 s. |
| `listen(board, seconds, expect)` | Read-only serial drain. Never writes. |

## Layout

- `protocol.py` — single source of truth for the framing (`F3…F4`, checksums, chunk/final shapes). `scripts/mbot_upload.py` is a thin CLI over it.
- `config.py` — board/port resolution from the environment.
- `server.py` — FastMCP stdio server exposing the four tools.

## Constraints

- USB only (the board's Bluetooth is BLE-GATT, not serial).
- Entry point of every uploaded file must stay `@event.start` — anything
  else bricks the board (boot logo, then dark).
- Physical confirmation (LED/screen) is the success signal, not logs.

Full rollout guide (per-OS prerequisites, fleet, hardware checklist,
releases, proof log): `docs/07-cyberpi-upload-mcp.md`.
