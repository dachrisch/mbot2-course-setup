# AGENTS.md — `cyberpi/`

MicroPython programs that run **on the CyberPi board** as `main.py` after an
upload. Nothing here executes in a PC interpreter or under pytest; there are no
mocks, and a change is only proven by uploading to a powered board.

## Hard constraints

- **The entry point must stay registered via `@event.start`** (from
  `import event`), never a bare top-level block or
  `if __name__ == "__main__":`. Confirmed 2026-09-06: a non-`@event.start`
  entry point boots to the Makeblock logo, then hangs/goes dark and needs a
  firmware reinstall — reproduced twice, independent of the code run.
  Re-test any structural change with a small marker-bearing snippet before
  trusting the full program. See
  `../history/2026-09-06_mlink-fix-and-bridge-upload-brick.md`.
- **Device APIs stay top-level imports** (`import cyberpi`, `import mbot2`,
  `import mbuild`), not `cyberpi.mbot2` / `cyberpi.ultrasonic2` attribute
  access.
- **Consult `../docs/05-cyberpi-mbot2-api-reference.md` before using any API
  call.** It holds the signatures confirmed on real hardware; don't guess.
- **Never suggest Arduino flashing** — it wipes CyberOS. These are
  MicroPython uploads that coexist with it.
- Uploads need the wire size `% 80 == 4`. The uploader pads with trailing
  newlines and leaves the file on disk untouched; other shapes are silently
  rejected and can hang the board until power-cycled. See
  [../src/AGENTS.md](../src/AGENTS.md).

## Conventions in this directory

- Every file carries a header comment with a unique `MARKER` string and prints
  it as a serial heartbeat. This is the upload proof when USB stdout is
  readable; physical LED/screen confirmation still wins because stdout is
  usually silent on this board.
- `welcome_greeter.py` — the demo (speak → dance → end text). `red_test.py` —
  minimal uploader end-to-end test (currently on the board as of 2026-09-19).
  `hi_cheer.py` — alternate greeting. `serial_probe.py`, `uart_probe.py`,
  `uart_probe2.py` — diagnostic probes only: no motors, no flash writes, safe
  to observe passively.

## Verify

```bash
wc -c cyberpi/welcome_greeter.py   # byte length; sanity-check the editor before uploading
```

Upload via the MCP `upload` tool (preferred), the CLI
(`sg dialout -c "python3 scripts/mbot_upload.py cyberpi/<file>.py"`), or the
`upload-cyberpi` browser skill as fallback. Close any mBlock tab first (port
contention), power-cycle if the program doesn't boot within ~20 s, and ask the
user to physically confirm the behavior.
