# CyberPi Welcome Greeter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace this repo's deleted PC-remote-control bridge with a
standalone CyberPi MicroPython program that plays a speak→dance→end-text
greeting sequence once at boot, and update the repo's docs to describe the
new purpose.

**Architecture:** A single MicroPython file, `cyberpi/welcome_greeter.py`,
with three small functions (`_speak_greet`, `_dance`, `_end_text`) called
in sequence from an `@event.start`-registered `on_start()`. No PC
communication, no serial protocol, no loop — it runs once per boot and
finishes. Built incrementally: each phase is written, uploaded to the real
board via the `upload-cyberpi` skill, and physically confirmed by the user
before the next phase is added, since this repo has no automated test
suite for on-device behavior and this session bricked the board twice
from unverified assumptions.

**Tech Stack:** MicroPython (CyberPi's on-device runtime), confirmed APIs
from `docs/05-cyberpi-mbot2-api-reference.md` (`cyberpi`, `mbot2`,
`mbuild`, `event` top-level modules).

**Spec:** `docs/superpowers/specs/2026-09-06-cyberpi-welcome-greeter-design.md`

## Global Constraints

- Entry point **must** be registered via `@event.start` from `import
  event` — never a bare `if __name__ == "__main__"` block. Confirmed
  2026-09-06: violating this bricked the board twice, independent of what
  the rest of the code did (see
  `history/2026-09-06_mlink-fix-and-bridge-upload-brick.md`).
- Device APIs are top-level imports: `import cyberpi`, `import mbot2`,
  `import mbuild`, `import event` — not `cyberpi.mbot2` attribute access.
- Every upload to the physical board goes through the `upload-cyberpi`
  skill (`.claude/skills/upload-cyberpi/SKILL.md`). Never restart the
  mlink daemon during an upload. Never declare an upload successful
  without the user physically confirming the board's behavior — the
  upload log and mBlock's own "Send" box have both produced misleading
  signals this session.
- No automated test suite exists for on-device behavior (`AGENTS.md`).
  Every "test" step in this plan is a real upload followed by the user
  physically observing and confirming the board's behavior — treat that
  confirmation as the pass/fail gate, exactly like a unit test's assertion.
- No default file path anywhere for the upload skill or these scripts —
  always pass/reference the exact path explicitly.

---

### Task 1: Boot skeleton + speak/greet phase

**Files:**
- Create: `cyberpi/welcome_greeter.py`

**Interfaces:**
- Produces: `_speak_greet()` — no args, no return value, plays the
  greeting (LED cyan, screen text, audio preset). `on_start()` —
  `@event.start`-registered entry point; at the end of this task it calls
  only `_speak_greet()`.

- [ ] **Step 1: Write the file**

```python
# cyberpi/welcome_greeter.py
# Standalone CyberPi greeter: plays a speak -> dance -> end-text sequence
# once at boot. No PC/serial/MCP involved. See
# docs/05-cyberpi-mbot2-api-reference.md for the API calls used here, and
# docs/superpowers/specs/2026-09-06-cyberpi-welcome-greeter-design.md for
# the design this implements.
#
# IMPORTANT: entry point must stay registered via @event.start (see
# history/2026-09-06_mlink-fix-and-bridge-upload-brick.md) — a bare
# `if __name__ == "__main__"` block bricked this board twice.

import cyberpi
import event
import mbot2


def _speak_greet():
    cyberpi.led.on(0, 255, 255, id='all')
    cyberpi.audio.set_vol(100)
    cyberpi.display.show_label("Hello!", 24, 0, 20, 0)
    cyberpi.audio.play_until("hello")


@event.start
def on_start():
    _speak_greet()
```

- [ ] **Step 2: Upload and verify (this task's test)**

Invoke the `upload-cyberpi` skill with
`path=cyberpi/welcome_greeter.py`. Follow its steps exactly (it will warn
if `@event.start` is missing — it should NOT warn here since it's present).

Expected physical result, to confirm with the user before proceeding:
cyan LED ring turns on, the screen shows "Hello!", and the built-in
"hello" audio clip plays. The board must remain responsive afterward (no
boot-logo-then-dark hang).

If the user reports anything other than this, STOP — do not proceed to
Task 2. Investigate per `history/2026-09-06_mlink-fix-and-bridge-upload-brick.md`'s
documented incident format rather than guessing at a fix.

- [ ] **Step 3: Commit**

```bash
git add cyberpi/welcome_greeter.py
git commit -m "feat: add CyberPi welcome greeter speak/greet phase

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NNyGXTz8uGdKF2GCHbvXaq"
```

---

### Task 2: Dance phase

**Files:**
- Modify: `cyberpi/welcome_greeter.py`

**Interfaces:**
- Consumes: nothing from Task 1 beyond the existing `on_start()` structure
  and the already-imported `cyberpi`, `mbot2` modules.
- Produces: `_dance()` — no args, no return value, runs the choreographed
  movement/LED/drum sequence. `on_start()` now calls `_speak_greet()` then
  `_dance()`.

- [ ] **Step 1: Add the dance function and wire it into `on_start`**

Edit `cyberpi/welcome_greeter.py`: add `_dance()` above `on_start`, and
update `on_start` to call it after `_speak_greet()`.

```python
def _dance():
    moves = [
        (lambda: mbot2.turn(90), (0, 255, 0), "snare"),
        (lambda: mbot2.turn(-90), (255, 0, 255), "tambourine"),
        (lambda: mbot2.forward(40, 0.4), (0, 255, 255), "side-stick"),
        (lambda: mbot2.backward(40, 0.4), (255, 255, 0), "hand-clap"),
    ]
    for _ in range(2):
        for move, color, drum in moves:
            cyberpi.led.on(color[0], color[1], color[2], id='all')
            cyberpi.audio.play_drum(drum, 0.3)
            move()
    cyberpi.led.play(name="rainbow")
```

```python
@event.start
def on_start():
    _speak_greet()
    _dance()
```

- [ ] **Step 2: Upload and verify (this task's test)**

Invoke the `upload-cyberpi` skill with `path=cyberpi/welcome_greeter.py`
again (full current file, both phases present).

Expected physical result to confirm with the user: after the greet phase,
the robot performs two rounds of turn-right/turn-left/forward/backward,
each accompanied by a different LED color and a distinct drum sound, then
the LED ring shows the "rainbow" animation. Board remains responsive
afterward.

If the user reports the board went dark/unresponsive, or any move/sound/
color didn't match, STOP — do not proceed to Task 3. Document per
`history/2026-09-06_mlink-fix-and-bridge-upload-brick.md`'s format.

- [ ] **Step 3: Commit**

```bash
git add cyberpi/welcome_greeter.py
git commit -m "feat: add dance phase to CyberPi welcome greeter

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NNyGXTz8uGdKF2GCHbvXaq"
```

---

### Task 3: End-text phase (completes the greeter)

**Files:**
- Modify: `cyberpi/welcome_greeter.py`

**Interfaces:**
- Consumes: nothing new beyond `cyberpi` (already imported).
- Produces: `_end_text()` — no args, no return value, clears LEDs/screen
  and shows the closing message. `on_start()` now calls all three phases
  in sequence: `_speak_greet()`, `_dance()`, `_end_text()`. This is the
  complete greeter — no further phases are added after this task.

- [ ] **Step 1: Add the end-text function and wire it into `on_start`**

```python
def _end_text():
    cyberpi.led.off(id='all')
    cyberpi.display.clear()
    cyberpi.display.show_label("Welcome to class!", 16, 0, 20, 0)
```

```python
@event.start
def on_start():
    _speak_greet()
    _dance()
    _end_text()
```

- [ ] **Step 2: Upload and verify (this task's test)**

Invoke the `upload-cyberpi` skill with `path=cyberpi/welcome_greeter.py`
(complete three-phase file).

Expected physical result to confirm with the user: the full sequence
plays end to end (greet, dance, then LEDs off / screen cleared / "Welcome
to class!" shown), board remains responsive, total runtime roughly
10-12 seconds.

If anything doesn't match, STOP and document rather than iterating blindly
— this is the last on-device change in this plan.

- [ ] **Step 3: Commit**

```bash
git add cyberpi/welcome_greeter.py
git commit -m "feat: add end-text phase, completing CyberPi welcome greeter

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NNyGXTz8uGdKF2GCHbvXaq"
```

---

### Task 4: Update `README.md` for the pivot

**Files:**
- Modify: `README.md`

**Interfaces:** None (documentation only).

- [ ] **Step 1: Rewrite `README.md`'s content to describe the greeter, not the MCP server**

Read the current `README.md` first (it still describes the deleted MCP
server, `pip install -e .`, `MBOT2_MOCK`, the tool list, and the
architecture diagram showing opencode → mbot2-mcp → serial). Replace it
with a description of:
- What this repo is now: a standalone CyberPi MicroPython program that
  greets people at boot (speak → dance → end text).
- How to upload it: via mBlock (`ide.mblock.cc`, Upload mode) manually, or
  via the `upload-cyberpi` skill.
- Link to `docs/05-cyberpi-mbot2-api-reference.md` for the API reference
  and `docs/superpowers/specs/2026-09-06-cyberpi-welcome-greeter-design.md`
  for the design.
- Keep the existing "Docs" section pointing at `docs/01-04` (mLink
  setup/upload/troubleshooting are still accurate for getting a browser
  connected to the board) and add `docs/05-cyberpi-mbot2-api-reference.md`
  to that list.
- Remove: the architecture diagram (opencode/MCP/serial), the "Quick
  start" `pip install`/`MBOT2_MOCK` section, the "Tools" list, the
  `opencode-mcp.example.json` reference (file no longer exists), and the
  Bluetooth-as-just-another-serial-port claim (already partially corrected
  earlier this session — fold that correction in rather than duplicating
  it).

There is no fixed template for the new wording — write it as a normal
README for the project as it now stands, matching this repo's existing
concise, example-driven style (see `AGENTS.md` for tone reference).

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README for the welcome-greeter pivot

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NNyGXTz8uGdKF2GCHbvXaq"
```

---

### Task 5: Update `AGENTS.md` for the pivot

**Files:**
- Modify: `AGENTS.md`

**Interfaces:** None (documentation only).

- [ ] **Step 1: Rewrite `AGENTS.md`'s content**

Read the current file first. Update:
- The opening description (currently: "Stdio MCP server... driving
  mBot2/CyberPi over serial") to describe the standalone greeter instead.
- The "Layout" section: remove references to `src/mbot2_mcp/*` (deleted)
  and `mbot2_bridge.py` (deleted, replaced by `welcome_greeter.py`); add
  `cyberpi/welcome_greeter.py` and `docs/05-cyberpi-mbot2-api-reference.md`.
- The "Hard constraints" section: **keep** the `@event.start`/top-level
  device-module-imports constraint (still fully applicable) and the
  Arduino-flashing warning (still applicable); **remove** the `mcp>=1,<2`
  pyproject constraint and the "0xFF 0x55 frame protocol" constraint
  (both were about the now-deleted PC-side bridge/server and no longer
  apply — there is no serial line protocol anymore).
- The "Commands" section: remove `pip install -e .` and the
  `mcp.list_tools()` verification snippet (package no longer exists);
  replace with how to upload/verify the greeter (reference the
  `upload-cyberpi` skill).
- Keep the "Serial gotchas" section's content that's about mLink/dialout/
  USB connectivity in general (still accurate for getting a browser
  connected to upload code) — just remove anything specifically about the
  MCP server's own serial probe commands that reference deleted files.

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: rewrite AGENTS.md for the welcome-greeter pivot

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NNyGXTz8uGdKF2GCHbvXaq"
```

---

### Task 6: Update `CLAUDE.md` for the pivot

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:** None (documentation only).

- [ ] **Step 1: Rewrite `CLAUDE.md`'s content**

Read the current file first (`CLAUDE.md` was written to mirror `AGENTS.md`
earlier this session, but is not byte-identical — read it directly rather
than assuming it matches `AGENTS.md`'s pre-edit content). Update:
- The "What this is" section (currently describes a stdio MCP server
  driving mBot2/CyberPi over serial, with the opencode/MCP/USB-serial
  architecture diagram) to instead describe the standalone greeter: a
  MicroPython program on the CyberPi that plays a speak→dance→end-text
  sequence once at boot, no PC/MCP/serial involved. Remove the
  architecture diagram.
- The "Layout" section: remove references to `src/mbot2_mcp/*` (deleted:
  `server.py`'s 12 MCP tools, `transport.py`, `config.py`) and
  `mbot2_bridge.py` (deleted, replaced); add `cyberpi/welcome_greeter.py`
  and `docs/05-cyberpi-mbot2-api-reference.md`.
- The "Commands" section: remove `pip install -e .`, the
  `MBOT2_MOCK=1 python3 -c "... mcp.list_tools() ..."` snippet, the
  `sg dialout -c "... SerialTransport ..."` PING snippet, and the
  `MBOT2_MOCK=1 python -m mbot2_mcp.server` snippet (all reference deleted
  code). Replace with: how to upload the greeter (reference the
  `upload-cyberpi` skill, `.claude/skills/upload-cyberpi/SKILL.md`) and
  `python scripts/list_ports.py` for finding the board's port (still
  applicable, unchanged).
- The "Configuration (env vars)" section: remove entirely —
  `MBOT2_MOCK`/`MBOT2_PORT`/`MBOT2_BOTS` no longer exist, there is no
  config to describe.
- The "Hard constraints" section: **keep** the `@event.start` +
  top-level-device-module-imports constraint and the Arduino-flashing
  warning (both still fully applicable); **remove** the `mcp>=1,<2`
  `pyproject.toml` constraint and the "0xFF 0x55 frame protocol" constraint
  (both were about the now-deleted PC-side bridge/server).
- The "Serial gotchas" and "When real hardware is actually needed"
  sections: keep content about mLink/dialout/USB connectivity in general
  (still accurate for getting a browser connected to upload code); remove
  anything specifically about the MCP server's own serial probe commands
  or `MBOT2_MOCK` mode.

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: rewrite CLAUDE.md for the welcome-greeter pivot

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NNyGXTz8uGdKF2GCHbvXaq"
```
