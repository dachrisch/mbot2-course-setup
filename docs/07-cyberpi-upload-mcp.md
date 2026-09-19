# cyberpi-upload MCP (upload-only, browser-free)

MCP server wrapping the browser-free USB upload protocol
(`docs/06-usb-upload-protocol.md`, single source of truth
`src/cyberpi_mcp/protocol.py`). No browser, no mLink. The old
`mbot2-mcp` live-control server (`drive`/`ultrasonic`/… over plain-text
stdin) was removed in `726e12e` and is **not** revived here: USB stdin is
dead (`repl_enable=False` persisted by the preamble) and the board's
Bluetooth is BLE-GATT only, not SPP
(`history/2026-09-08_browser-free-upload.md`,
`history/2026-09-06_mlink-fix-and-bridge-upload-brick.md` Part 7).

## Rollout

The server is plain stdio + pyserial: any MCP client on any OS works.
USB only on all platforms — the board's Bluetooth is BLE-GATT, not a
serial port, so there is no wireless path for these tools.

### 1. Per-OS prerequisites

| OS | USB-serial driver (CH340 `1a86:7523`) | Find the port | Permissions |
|---|---|---|---|
| Linux | In-kernel (`ch341`); nothing to install. Verify: `lsusb \| grep 1a86` | `/dev/ttyUSB0` (`python3 scripts/list_ports.py` before/after plugging) | Port is `root:dialout` mode 660: `sudo usermod -aG dialout $USER`, then log out/in. Until then prefix everything with `sg dialout -c "..."`. Never use sudo to dodge this (breaks `pip install -e .` visibility). |
| macOS | Vendor driver required (WCH CH34x VCP); approve it in System Settings if prompted, then replug | `/dev/tty.wchusbserial*` (same `list_ports.py` before/after check) | None beyond the driver approval. |
| Windows | Vendor driver required (WCH CH34x); check Device Manager → Ports | `COMx` (e.g. `COM6`; whatever Device Manager shows for the CH340) | None. Use Python from python.org/`winget` with `py` or `python` on PATH. |

Python `>=3.10` on all three. No mLink, no browser, no admin rights
(except the one-time Linux `dialout` fix / driver installs).

### 2. Install (all OSes)

```bash
cd <this-repo>
pip install -e .
python -m pytest tests/ -q   # 11 passed == good to roll
```

Windows: `py -m pytest tests/ -q`. Prefer a venv if Python packaging
complains about externally-managed environments (Debian/Ubuntu):
`python3 -m venv .venv && .venv/bin/pip install -e .`.

### 3. Configure the client

Single board — set `CYBERPI_PORT` to the port from step 1:

**opencode** (`~/.config/opencode/opencode.json` on Linux/macOS,
`%APPDATA%/opencode/opencode.json` on Windows; full example in
`opencode-mcp.example.json`):

```json
{ "mcp": { "cyberpi-upload": {
  "type": "local",
  "command": ["python", "-m", "cyberpi_mcp.server"],
  "enabled": true,
  "environment": { "CYBERPI_PORT": "/dev/ttyUSB0" }
} } }
```

Windows: `"command": ["py", "-m", "cyberpi_mcp.server"]`,
`"CYBERPI_PORT": "COM6"`. macOS: `"CYBERPI_PORT":
"/dev/tty.wchusbserial110"` (your suffix will differ).

**Claude Code** (same machine, same env var):

```bash
export CYBERPI_PORT=/dev/ttyUSB0   # COM6 / /dev/tty.wchusbserial* elsewhere
claude mcp add cyberpi-upload -- python -m cyberpi_mcp.server -e CYBERPI_PORT=$CYBERPI_PORT
```

**Fleet** (course setup, one entry per serial port — same syntax all OSes,
just mix port styles): `CYBERPI_BOTS="A=/dev/ttyUSB0,B=/dev/ttyUSB1"`
or `"A=COM6,B=COM7"`. The `upload`/`listen` tools take `board: "A"`.

**Hardware-free dev / CI:** `CYBERPI_MOCK=1` — every tool returns
deterministic fakes, no port needed, server still starts.

### 4. Verify the rollout (each machine, ~5 min, needs the bot)

1. Cable in (data cable, not charge-only), bot power switch **ON**
   (sensor LEDs lit — the port enumerates even with power off but stays
   silent).
2. Close any mBlock IDE tab (it polls the port via mLink).
3. `python3 scripts/list_ports.py` → your port is listed.
4. `check_file` on the file you intend to upload (warns if `@event.start`
   is missing — stop and fix unless you have a reason).
5. `upload(path)` → all frames acked. If no boot within ~20 s,
   power-cycle the bot (side switch OFF/ON) before assuming failure.
6. User physically confirms the board's behavior (LED/screen). That
   confirmation — not logs, not markers — is the success criterion
   (USB stdout is currently silent on this board; see Proof log).

## Tools (4)

| Tool | What it does |
|---|---|
| `check_file(path)` | Pre-upload check: disk bytes, wire bytes (`%80==4` after auto-pad), `@event.start` guard. Warns, does not block, when the guard is missing. |
| `list_local()` | `cyberpi/*.py` with size + guard status. |
| `upload(path, board, expect_marker)` | Full upload over USB serial; optional 20 s marker wait. Returns `power_cycle_hint: true` when a marker was expected but not seen — power-cycle before assuming failure. Failed uploads leave the live program intact (staging slot). |
| `listen(board, seconds, expect)` | Read-only serial drain for program output / marker. Never writes. |

## Constraints (same as the CLI)

- Exclusive port access: close any mBlock IDE tab first (mLink polls).
- `sg dialout -c ...` if the session predates the `dialout` group fix.
- Entry point must stay `@event.start` (`AGENTS.md` hard constraint).
- Only `size % 80 == 4` wire shapes; padding is trailing `\n` in memory.

## Verifying on hardware

```bash
sg dialout -c "python3 scripts/mbot_upload.py cyberpi/red_test.py"
# or via MCP: upload(red_test.py) -> user confirms red LED ring
```

The only trustworthy success signal is the user physically confirming the
board's behavior. The `upload-cyberpi` skill (browser path) remains as a
fallback and its physical-check rule applies here too.

## Releases (release-please + artifacts)

Every push to `main` runs release-please (`.github/workflows/release-please.yml`):
conventional commits (`feat:`/`fix:`/…) since the last release accumulate
into a **release PR** (`chore(main): release x.y.z`) that bumps the version
in `pyproject.toml` and updates the changelog. Merging that PR tags
`cyberpi-upload-mcp-vx.y.z` and publishes a GitHub Release — so keep commit
messages conventional (`feat:`, `fix:`, `docs:` …), this repo already does.

Publishing a release triggers `.github/workflows/release-artifacts.yml`,
which builds the sdist + wheel (`python -m build`) and attaches
`dist/*` to the release. Install a pinned release anywhere without git:

```bash
pip install https://github.com/dachrisch/mbot2-course-setup/releases/download/cyberpi-upload-mcp-v0.1.0/cyberpi_upload_mcp-0.1.0-py3-none-any.whl
# (replace the version/tag with the latest release)
export CYBERPI_PORT=/dev/ttyUSB0   # COM6 / /dev/tty.wchusbserial* elsewhere
python -m cyberpi_mcp.server
```

First release note: with no prior tags, the first release PR cuts `0.1.0`
from `pyproject.toml`; afterwards versioning is fully automatic.

## Proof log

- 2026-09-19: first upload through the MCP itself —
  `upload(cyberpi/red_test.py)` in real mode, all 19 frames acked first
  try (804 B, `%80==4` natively). Board needed a physical power cycle
  before booting the new program (same as raw-serial CLI runs). User
  confirmed red LED ring + "RED test" title. Wire marker
  (`RED-TEST-9F1C4`) was **not** seen on serial in two `listen` windows
  (10 s, 15 s; 0 bytes) despite the program demonstrably running —
  consistent with the `repl_enable=False` lead in
  `docs/06-usb-upload-protocol.md` (USB stdout silent on this board).
  Physical confirmation remains the success criterion, not the marker.
