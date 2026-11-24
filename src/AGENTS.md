# AGENTS.md — `src/`

The `cyberpi_mcp` package: an upload-only MCP server (no browser, no mLink, no
live drive/sensor control) that replays the mBlock USB upload framing over
`pyserial`. Its user-facing docs are `cyberpi_mcp/README.md` and
`../docs/07-cyberpi-upload-mcp.md`.

## Hard constraints

- **`cyberpi_mcp/protocol.py` is the single source of truth for framing**
  (`F3…F4`, checksum, chunk/final shapes). `../scripts/mbot_upload.py` is a
  thin CLI shim over it — change framing in `protocol.py`, never in the CLI.
  The PING/EXEC bytes are byte-identical captures from the mBlock session;
  don't "clean up" those constants without re-capturing.
- **The board only accepts wire sizes `% 80 == 4`.** `pad_to_wire_size()`
  appends trailing newlines (semantically null in Python) and leaves the disk
  file untouched. Short tails or non-4-byte finals are silently rejected and
  can hang the board until power-cycled.
- **No port configured → safe mock**, so the server still starts. Don't make
  imports require real hardware; `CYBERPI_MOCK=1` is the supported dev mode.
- Upload needs exclusive port access: close any mBlock tab first. A failed
  upload leaves the running program intact (staging slot). Physical
  LED/screen confirmation is the success signal, not logs.

## Layout and config

- `cyberpi_mcp/protocol.py` — framing builders, `read_frame`/`transact`,
  `upload()`; `config.py` — board/port resolution; `server.py` — stdio MCP
  server with four tools (`check_file`, `list_local`, `upload`, `listen`).
  `check_file`/`upload` only **warn** on a missing `@event.start`; `listen`
  is read-only and never writes to the board.
- Env knobs: `CYBERPI_PORT` (single board), `CYBERPI_BOTS="A=/dev/ttyUSB0,B=/dev/ttyUSB1"`
  (fleet), `CYBERPI_MOCK=1` (hardware-free).
- `server.py` supports both mcp 2.x (`MCPServer`) and 1.x (`FastMCP`); keep the
  fallback when touching the server import.
- Console entry point / manual start: `cyberpi-upload`, or
  `python -m cyberpi_mcp.server`.

## Commands

```bash
pip install -e .                   # from the repo root
python3 -m pytest tests/ -q        # 11 hardware-free tests; see ../tests/AGENTS.md
python -m cyberpi_mcp.server       # stdio MCP server
```

Wiring examples: `../opencode-mcp.example.json` and
`../src/cyberpi_mcp/README.md`. On-device rules for the files being uploaded
live in [../cyberpi/AGENTS.md](../cyberpi/AGENTS.md).
