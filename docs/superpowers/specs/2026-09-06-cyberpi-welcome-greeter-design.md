# CyberPi welcome greeter — design

Status: approved by user, ready for implementation planning.

## Purpose

Pivot this repo from a PC-side MCP server that remote-controls an mBot2
over serial, to a standalone on-device CyberPi program that greets kids
when the robot powers on. No PC, MCP server, or serial connection is
needed for this behavior — it runs autonomously on the board.

This is a full pivot, not an addition: the MCP server (`src/mbot2_mcp/*`,
`pyproject.toml`, `opencode-mcp.example.json`) has already been removed
from the repo at the user's request. The generic remote-control bridge
(`cyberpi/mbot2_bridge.py`) was already deleted in favor of this
purpose-built script.

## Trigger

Boot/power-on only. No sensor-based detection (no "someone approached"
logic) — the greeting plays once every time the CyberPi starts up,
registered via `@event.start` per this repo's confirmed hard constraint
(see `AGENTS.md` and `history/2026-09-06_mlink-fix-and-bridge-upload-brick.md`).

## Behavior

Single-shot sequence, roughly 10-12 seconds total, then the program is
done (no loop, no ongoing serial listener):

1. **Speak & greet (~2s).** Cyan LED ring, "Hello!" on screen, plays the
   built-in `"hello"` audio preset (`cyberpi.audio.play_until("hello")`)
   — offline, no WiFi/cloud dependency. (Real text-to-speech via
   `cyberpi.cloud.tts()` exists but requires WiFi and a Makeblock cloud
   token; explicitly deferred as a future enhancement, not needed for v1.)
2. **Dance (~6-8s).** A short choreographed sequence alternating movement
   (`mbot2.turn`/`forward`/`backward`), LED color, and a drum hit
   (`cyberpi.audio.play_drum`) per beat, run twice through, ending with
   the built-in `cyberpi.led.play("rainbow")` animation. Movement calls
   block for their given duration (confirmed via community examples), so
   this is a sequential, not truly parallel, choreography — deliberately
   avoiding MicroPython threading given this session's history of two
   firmware-bricking incidents from runtime-structure mistakes.
3. **End text (~2s).** LEDs off, screen cleared, closing message shown:
   "Welcome to class!".

Exact moves/colors/sounds per phase, as approved in chat:

```python
moves = [
    (lambda: mbot2.turn(90),          (0, 255, 0),   "snare"),
    (lambda: mbot2.turn(-90),         (255, 0, 255), "tambourine"),
    (lambda: mbot2.forward(40, 0.4),  (0, 255, 255), "side-stick"),
    (lambda: mbot2.backward(40, 0.4), (255, 255, 0), "hand-clap"),
]
```

## File layout

- New file: `cyberpi/welcome_greeter.py` — the on-device program, uploaded
  as `main.py` via mBlock (manually or via the `upload-cyberpi` skill).
- `docs/05-cyberpi-mbot2-api-reference.md` (already written) documents the
  confirmed API calls this script relies on, sourced from inspecting
  `PerfecXX/mBot2`.
- `README.md`, `AGENTS.md`, `CLAUDE.md` need updating to describe the new
  purpose (welcome greeter) instead of the old MCP-server description —
  removing stale references to `pip install -e .`, `MBOT2_MOCK`, the MCP
  tool list, etc.

## Testing / rollout plan

Upload via the `upload-cyberpi` skill (`.claude/skills/upload-cyberpi/`),
which already encodes this session's hard-won lessons (verify
`@event.start` present, byte-for-byte content check, never assume success
from the log, always get physical confirmation from the user afterward).

Verification is necessarily physical/observational (LED colors, screen
text, motion, sound), not automated — there is no PC-side test harness for
this behavior anymore (no MCP server, no serial protocol to probe).

## Explicitly out of scope for this design

- **Multi-bot interaction.** The user's stated future direction ("later so
  bots interact with each other") is not designed here. The most promising
  confirmed mechanism found so far is `cyberpi.wifi_broadcast.set/get(topic,
  message)` (same-WiFi pub/sub between bots, no Bluetooth or MCP server
  needed) — documented in `docs/05-cyberpi-mbot2-api-reference.md` for
  when that phase is designed, but not part of this implementation.
- **Cloud text-to-speech.** Noted above as a possible future upgrade to the
  "speak" phase; not implemented now (adds WiFi + Makeblock cloud
  credential dependency for a v1 that doesn't need it).
- **Sensor-triggered greeting** (e.g. ultrasonic-based "someone approached"
  detection). User explicitly chose boot-triggered only.
