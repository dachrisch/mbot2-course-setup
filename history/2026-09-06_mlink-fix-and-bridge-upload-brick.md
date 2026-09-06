# 2026-09-06 — mLink permission fix, then two brick incidents, then confirmed root cause

## Summary

Fixed a stale-login-session permission bug that was blocking mLink from
reaching the bot's serial port. Once mLink could connect, the user uploaded
`cyberpi/mbot2_bridge.py` via the mBlock web IDE (python.mblock.cc) — and the
CyberPi came out of that bricked. After a firmware reinstall, this agent
uploaded code via `ide.mblock.cc` (block-based IDE, Python tab) twice more —
once the full bridge script, once a trivial one-line `print("hello")` — and
**both uploads produced the same symptom**: CyberPi shows the Makeblock boot
logo briefly then goes dark/unresponsive, requiring a second firmware
reinstall.

**Root cause confirmed in Part 5:** CyberPi's runtime (under `ide.mblock.cc`
Upload mode, at least) requires the uploaded program's entry point to be
registered via `@event.start` from Makeblock's `event` module. Neither
failing upload did this (bare top-level code / `if __name__ == "__main__"`).
A minimal `@event.start`-based test program, uploaded after the second
reinstall (this time over **Bluetooth**, no USB), booted and ran
successfully with a unique marker string to rule out stale/cached code.
**`mbot2_bridge.py` needs to be restructured around `@event.start` before
it is ever uploaded again** — see Part 5 for the specific required changes.

**Standing instruction as of this writing: do not upload anything to this
CyberPi, or touch mlink/the serial port, without explicit user go-ahead.**
Two firmware reinstalls in one session is enough — even with the root cause
now confirmed, re-test incrementally (small marker-bearing snippets) before
trusting the full bridge script again.

## Part 1 — mLink connection problem (resolved)

**Symptom:** mLink installed and running (`mlink start`, listening on
`:55278`), CH340 chip visible in `lsusb`, `/dev/ttyUSB0` present with correct
`root:dialout crw-rw----` permissions — but mBlock could not connect to the
bot.

**Root cause:** `sudo usermod -aG dialout $USER` had been run at 10:08:39,
but the desktop login session (and everything forked from it, including the
already-running `mlink` daemon, started 10:21:56) predated that change and
still carried the old group list without `dialout`. `id <user>` misleadingly
showed `dialout` (it re-reads `/etc/group` live), masking the fact that the
*running session* didn't have it.

**Fix:**
1. User logged out and back in (refreshes the desktop session's groups).
2. mlink daemon was relaunched with `sg dialout -c ...` to force the
   effective GID to `dialout` for that process, since simply restarting it
   from a shell that predated the logout wasn't sufficient inside this
   agent's own tool sandbox (see gotcha below).
3. Verified via `/proc/<pid>/status` → `Gid: 20 20 20 20` (effective GID
   dialout) and a direct `pyserial` open of `/dev/ttyUSB0` succeeding with no
   `Permission denied` / `Device or resource busy`.

**Tooling gotcha hit along the way (not a repo bug, just a caveat for next
time):** this agent's Bash tool backgrounds any command that runs past its
~120s timeout by reparenting it, and that reparenting silently drops a
`sg`-elevated effective GID back to the shell's original one. Verified by
checking `Gid:` (effective) vs `Groups:` (supplementary-only) in
`/proc/<pid>/status` — an earlier check that only looked at `Groups:` gave a
false negative. Workaround: wrap the daemon launch in a script that
self-daemonizes with `setsid ... &; disown` and returns immediately, so the
wrapping shell exits well under the timeout and the tool never intervenes.

**Verification at the time:** with mlink running under effective GID
`dialout`, a raw `PING\n` over `/dev/ttyUSB0` at 115200 baud opened the port
cleanly but got no reply — expected, since the bridge wasn't uploaded yet.

## Part 2 — bridge upload bricked the CyberPi (unresolved, user recovering)

After the above fix, the user opened `python.mblock.cc`, connected via
mLink, and uploaded `cyberpi/mbot2_bridge.py` as `main.py` per
`docs/02-bridge-upload.md`. The CyberPi came out of that unresponsive
("bricked"); the user is currently reinstalling its firmware to recover.

**What we know:**
- The upload happened through the mBlock **web** IDE's Python upload path
  (not a local mBlock 5 client — none exists for Linux, see
  `docs/01-linux-setup.md`).
- Immediately prior, this agent had stopped/restarted the mlink daemon
  several times while diagnosing Part 1 (see command history: `mlink stop` /
  `mlink start` cycles between 10:21 and 10:56). **It's possible, but not
  confirmed, that a browser tab already connected to the old mlink process
  had a connection/upload interrupted by one of these daemon restarts.**
  This is a real candidate root cause and should be avoided going forward:
  don't restart mlink while a browser upload could be in flight.
- `cyberpi/mbot2_bridge.py` itself is plain MicroPython using documented
  `cyberpi`/`cyberpi.mbot2` APIs — nothing in it should be capable of wiping
  firmware; MicroPython `main.py` uploads are supposed to coexist with
  CyberOS (this was a hard constraint already documented in `AGENTS.md`
  precisely because the *other* known failure mode — Arduino-mode flashing —
  wipes CyberOS entirely). Whether this upload silently went through an
  Arduion-flash code path instead of the Python "Upload Mode" is unconfirmed.
- No content or timing details of the actual browser upload were captured
  (this agent does not have visibility into the mBlock web UI) — the mBlock
  console output, exact upload mode selected, and any error dialog shown at
  the time are not recorded anywhere.

**Open questions for whoever resumes this:**
1. Was "Upload Mode" (Python) definitely selected in mBlock, vs. some
   default/Arduino path?
2. Did the mBlock UI show an error or did the upload appear to finish
   normally before the bot went unresponsive?
3. Was the mlink daemon restarted (by this agent, mid-diagnosis) while the
   browser tab held an active connection to the bot?
4. After firmware reinstall, does the CH340/mLink connection still need the
   `dialout`/session fix from Part 1, or does firmware reinstall reset
   something that changes that story?

**Action items before re-attempting any upload:**
- Don't touch/restart the mlink daemon while a browser upload is in progress
  or might be.
- Re-verify "Upload Mode" is explicitly selected before clicking Upload.
- Consider the direct-serial alternatives being researched in parallel (see
  below) to avoid the mBlock web upload path entirely for future
  bridge updates.

### Refined root-cause theory (leading hypothesis, still unconfirmed)

Web research (2026-09-06, see below) surfaced two facts that sharpen the
theory beyond "maybe Arduino mode got selected by accident":

1. Multiple independent sources agree a plain MicroPython/Python **Upload**
   in mBlock only writes `main.py` and explicitly does **not** touch
   firmware — only Arduino-mode flashing does that. A simple bad upload
   should at worst boot-loop into a script error, still leaving the REPL
   reachable — not require a firmware reinstall.
2. Makeblock has a *separate*, known flow: mBlock can detect a firmware
   version mismatch on connect and trigger an **automatic firmware update**
   (Makeblock help center: "Update the Firmware of CyberPi"; a public forum
   thread exists titled "Cyberpi stuck in firmware update loop" describing
   exactly this going wrong).

Given this agent was actively stopping/restarting the mlink daemon
(`mlink stop` / `mlink start`, several cycles between 10:21–10:56) while the
user had a browser tab open against the CyberPi, **the most likely trigger
is one of those restarts interrupting an in-progress firmware update that
mBlock silently kicked off on connect** — not the `mbot2_bridge.py` upload
itself. This is a firmware-level write, which matches "bricked, needs
firmware reinstall" far better than a bad `main.py` would.

**Takeaway:** never touch/restart mlink while any mBlock browser tab is open
against the bot, and watch for any "updating firmware" indicator in the
mBlock UI before assuming a plain code upload is what's running.

## Research — can we connect more directly, bypassing the mBlock web IDE?

Prompted by this incident: could the MCP-side workflow (upload the bridge,
iterate on it) avoid the browser/mLink/mBlock stack entirely and talk to the
CyberPi with a plain serial tool instead?

**What already bypasses the web, confirmed working:** once
`mbot2_bridge.py` is running as `main.py`, this repo's own
`SerialTransport`/`PING` test talks to it over `/dev/ttyUSB0` with plain
text lines — no mLink, no browser, no Makeblock software involved at all.
The *runtime* control path is already fully direct. Only the **upload**
step (getting new code onto the board in the first place) currently
requires mBlock's web IDE + mLink.

**Whether the upload step can be made direct is unconfirmed:**
- CyberPi's CPU is ESP32-based and its Python layer is MicroPython
  underneath (`import cyberpi as cpi` is a normal MicroPython module import,
  consistent with a lightly-customized MicroPython firmware). Standard
  MicroPython boards typically expose a **raw REPL** (Ctrl-A / Ctrl-D
  paste-mode protocol) directly on the USB-CDC serial port, which is exactly
  what generic tools like `mpremote`, `ampy`, `rshell`, and Thonny use to
  transfer files — no vendor daemon required.
- No public documentation, forum post, or example repo was found (searched
  the Makeblock help center, Makeblock forum, and the community repos
  `icelam/cyberpi` and `PerfecXX/mBot2`) confirming that CyberPi's raw REPL
  is actually reachable this way, or that it isn't. All official material
  only describes the mBlock IDE path. This is a real gap, not a "no."
- Makeblock's own help center explicitly separates a "firmware update" flow
  from the Python upload flow, which suggests mBlock's connection handling
  does more than just open a plain serial port (e.g., version-checking
  handshakes) — but that doesn't preclude the underlying MicroPython raw
  REPL still being present and usable independently.

**Recommended next step (non-destructive, do only once the current
firmware reinstall is finished and the bot is confirmed healthy):**
Probe for a standard MicroPython raw REPL directly, without writing
anything:
```bash
# after re-verifying PING/OK PONG works normally over the bridge first
python3 -c "
import serial, time
s = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
s.write(b'\r\x01')      # Ctrl-A: enter raw REPL
time.sleep(0.3)
print(s.read(200))       # expect something like b'raw REPL; CTRL-B to exit\r\n>'
s.write(b'\x02')         # Ctrl-B: back to normal REPL/friendly banner
time.sleep(0.3)
print(s.read(200))
"
```
If this returns the standard MicroPython raw-REPL banner, `mpremote`/`ampy`
almost certainly work directly against `/dev/ttyUSB0` for both running code
*and* uploading `main.py`, and the mBlock web IDE could be reserved for
firmware updates only — removing the main risk surface hit today. If it
returns garbage or nothing, CyberPi's serial link is likely gated behind
mLink's proprietary protocol and the web IDE stays required for uploads.
This probe only reads/writes REPL control bytes — it does not write any
file to the board — so it's safe to try but is explicitly **not being run
now** per the no-further-writes instruction while firmware recovery is in
progress.

## Part 3 — second and third bricks, via ide.mblock.cc, code content ruled out

After the Part 2 brick and firmware reinstall, the user asked this agent to
do the upload directly using browser automation (Claude in Chrome), and
manually connected via mLink in Upload mode first (working around the
`python.mblock.cc` "mLink 2 required" dead end documented below).

**Attempt A — full bridge script:**
1. Verified `ide.mblock.cc` showed a live mLink connection (green dot),
   Upload mode selected.
2. Set the Monaco Python editor's content directly via
   `monaco.editor.getModels()[0].setValue(...)` (chosen over simulated
   keystrokes specifically to avoid editor auto-indent corrupting the
   script). Verified byte-for-byte: UTF-8 byte length matched the local
   file exactly (6107 bytes), line count matched (196).
3. Clicked "Upload Code". Progress dialog completed 0→100%, log showed a
   normal-looking sequence (`processing code by middleware of codey`,
   `...of intl`, `processing code completed`, `parse code upload by
   driver`, `start uploading......`) and closed itself — no error.
4. Bottom log panel showed binary-framed packets (hex, prefixed `f0`/`f3`)
   throughout, including one that decoded to plain ASCII `PYB: fast reboot`
   — the normal MicroPython post-upload reboot message, embedded inside the
   framing rather than appearing as bare text.
5. Disconnected cleanly via the UI ("The device has been disconnected").
6. Verified via raw `pyserial` against `/dev/ttyUSB0`: port opened with no
   `Permission denied`/`Device or resource busy` (mLink had fully released
   it), but `PING\n` got **no response**, and a raw Ctrl-C (`\r\x03`) —
   which should produce a `KeyboardInterrupt` + `>>>` REPL prompt in
   essentially any MicroPython state — also got **zero bytes back**.
7. User then reported: display had gone dark (from an options/menu screen
   that was up before the upload); after power-cycling, it shows the
   Makeblock boot logo briefly, then goes dark again. User began a second
   firmware reinstall.

**Attempt B — trivial script, to isolate cause (done with explicit user
approval, after user reconnected via mLink again):**
1. Replaced editor content with exactly `print("hello")\n` (15 bytes, 2
   lines) via the same `setValue` approach. Verified content.
2. Clicked "Upload Code" — toast said "The code has been uploaded"
   (this time fast enough that no progress dialog appeared at all).
3. Checked the log panel's full text (`document.body.innerText`) for the
   hex encoding of "hello" (`68 65 6c 6c 6f`) — **not found anywhere**,
   confirming plain `print()` stdout is not surfaced in that log either.
4. Disconnected via the UI, then checked raw serial again: **total
   silence** for 5s of passive listening — no boot banner, nothing.
5. User reported: same symptom as Attempt A — no luck, reinstalling
   firmware again.

**What this rules in/out:**
- **Ruled out:** anything specific to `mbot2_bridge.py`'s content. A
  single-line script with no loop, no display/LED calls, and no stdin
  interaction produced the identical dark-screen-after-logo symptom. The
  earlier "tight polling loop starves the watchdog/BLE stack" theory from
  this agent is very likely wrong — attempt B had no loop at all.
- **Ruled out (probably):** the Part 2 theory that *this agent's mlink
  daemon restarts* caused the original brick by interrupting a firmware
  update. Attempt B happened with this agent making zero changes to mlink
  or the daemon — the user connected and drove the mBlock UI state
  themselves for both attempts in Part 3 (this agent only edited the
  Monaco buffer and clicked "Upload Code"/"Disconnect") — and still bricked.
- **Strengthened:** raw serial (`/dev/ttyUSB0`) never shows plain-text
  stdout from an uploaded script, before *or* after the crash, regardless of
  script complexity — the CyberPi's serial line under this mLink/mBlock
  connection path appears to always be wrapped in Makeblock's own
  binary-framed protocol (the `f0`/`f3 ...` packets), not a bare MicroPython
  stdio passthrough. This means `mbot2_bridge.py`'s core assumption (plain
  text lines on the wire) may be incompatible with however this specific,
  freshly-reinstalled firmware now runs uploaded code — independent of the
  crash issue.
- **Leading open hypothesis:** something about `ide.mblock.cc`'s "Upload
  Code" action itself (in Upload mode) — not the uploaded code's content —
  is what's putting this particular CyberPi/firmware combination into a bad
  state after reboot. This was not observed with the original, pre-brick
  `python.mblock.cc` flow described in `docs/02-bridge-upload.md` (that
  route is now blocked entirely by the separate "mLink 2 required, no Linux
  build exists" issue — see Research section above — which is *why*
  `ide.mblock.cc` was tried at all). Whether `ide.mblock.cc`'s Upload Code
  path is fundamentally different/riskier than the one that worked earlier
  today, or whether the freshly-reinstalled firmware itself behaves
  differently now, is unknown.

**Do not repeat without new information:**
- Don't upload anything via `ide.mblock.cc` Upload mode again on this board
  without discussing it first — it has now produced this symptom twice with
  unrelated code.
- The still-unrun, non-destructive raw-REPL probe (see Research section
  above) is a safer next diagnostic than another upload attempt: it only
  sends REPL control bytes (Ctrl-A/Ctrl-B), never writes a file, and would
  tell us whether a plain MicroPython interpreter is even reachable on this
  port at all right now.
- Consider asking Makeblock support directly, given two reproducible bricks
  from unrelated code content strongly suggests a firmware/tooling bug
  rather than anything in this repo.

## Part 4 — new lead: missing `@event.start` structure

User provided a program they confirm previously worked via USB upload:

```python
import cyberpi
import mbot2
import mbuild
import time
import event

@event.start
def on_start():
    cyberpi.console.print("mBot2 Ready!")
    while True:
        distance = mbuild.ultrasonic2.get(1)
        if distance < 15:
            cyberpi.led.on('red')
            mbot2.turn(90)
        else:
            cyberpi.led.on('green')
            mbot2.forward(30)
        time.sleep(0.1)
```

This is structurally very different from both of this agent's uploads
(the full `mbot2_bridge.py` and the trivial `print("hello")`):

- It imports Makeblock's `event` module and registers its logic via an
  `@event.start` decorator, rather than running top-level code directly or
  via a bare `if __name__ == "__main__": main()` block.
- Module names differ too: top-level `import mbot2` / `import mbuild`,
  vs. this repo's `import cyberpi as cpi` + `getattr(cpi, "mbot2", None)`
  and `cyberpi.ultrasonic2`/`cyberpi.quad_rgb_sensor` (accessed as
  attributes of the `cyberpi` module rather than separate top-level
  modules). Both call conventions appear in the wild across
  Makeblock/community examples — this repo's bridge script followed one
  convention (based on searches during Part 2's research), the user's known
  working example follows the other.

**Working hypothesis:** CyberPi's on-device runtime (at least as driven
through `ide.mblock.cc`'s Upload mode) expects uploaded code to hand control
to its own event/scheduler system via `@event.start`, which likely handles
housekeeping (watchdog, screen, BLE/Wi-Fi service) between calls into user
code. Neither of this agent's uploads did this — the trivial `print("hello")`
had no event registration at all, and the full bridge script drove `main()`
directly with a bare blocking loop. If the runtime does not tolerate
top-level code that never yields back to it (or never registers with it in
the first place), that would produce exactly the observed symptom
(boots, shows logo, then hangs/goes dark) **regardless of what the
user code actually does** — matching both failed attempts.

This does not yet explain why the very first bridge upload today (Part 2,
via `python.mblock.cc`, before any of this agent's mlink fiddling) may have
also gone wrong — unless that upload never actually completed/ran
successfully in the first place and the mlink-restart theory (Part 2) or
something else was the real cause there. The two failure modes may be
unrelated.

**Suggested next test, once firmware is reinstalled and healthy, with
explicit user go-ahead before touching anything:** upload the user's
known-working `@event.start`-based program as-is (unmodified) via
`ide.mblock.cc` Upload mode, and confirm the board boots and stays
responsive. If it does, the fix for `mbot2_bridge.py` is to restructure it
around `@event.start`/`event` (or whatever minimal event registration the
runtime requires) instead of a bare blocking loop, before ever uploading it
again.

## Part 5 — CONFIRMED: `@event.start` registration is the fix

After a second firmware reinstall (device connected via **Bluetooth** this
time — no USB cable; `/dev/ttyUSB0` is expected to be absent in this mode,
`SerialTransport` would instead target a `/dev/rfcomm*`-style port per
`config.py`'s existing `MBOT2_BOTS`/`MBOT2_PORT` mechanism), this agent
uploaded a minimal test program via `ide.mblock.cc` (Bluetooth connection,
Upload mode), set via the same `monaco.editor.getModels()[0].setValue(...)`
approach as before, with a unique marker to rule out stale/cached code:

```python
import cyberpi
import mbot2
import mbuild
import time
import event

@event.start
def on_start():
    cyberpi.console.print("mBot2 Ready!")
    cyberpi.led.on('yellow')
    cyberpi.console.print("PROBE-QZX471")
```

Confirmed via the hex log that this exact code (marker included) was what
got transmitted, not a cached/stale payload. Upload completed normally
("The code has been uploaded"). **User confirmed: success** — board stayed
healthy, no dark-screen symptom.

**Root cause is now confirmed, not just hypothesized:** CyberPi's on-device
runtime (at least when driven through `ide.mblock.cc` Upload mode) requires
uploaded code to register its entry point via `@event.start`. Bare top-level
code or a plain `if __name__ == "__main__": main()` block — which is what
`mbot2_bridge.py` and the earlier trivial `print("hello")` test both used —
puts the board into the boot-logo-then-dark hang seen in Parts 2–3,
regardless of what the code actually does. A `while True` loop *inside* an
`@event.start`-decorated function is fine (the working example above has
one) — the requirement is specifically about how the entry point is
registered, not about avoiding loops.

## Part 6 — rewritten bridge uploaded and confirmed non-crashing

`mbot2_bridge.py` was rewritten per the fix below (entry point moved to
`@event.start def on_start()`, imports switched to top-level `mbot2`/
`mbuild`, bumped to `v0.2.0`). Uploaded via `ide.mblock.cc` over the same
Bluetooth connection as Part 5, using the same `monaco.editor.setValue`
approach with byte-length verification (6580 bytes matched exactly).

Upload completed normally. mBlock's log showed only chunk-echoes of our own
source being transferred (decoded several as sanity checks — e.g. literal
`if len(buf) > 200:  # safety: drop overlong lines` — confirming the
correct file content reached the device), not any error/traceback.

**User confirmed the boot LED blip (blue flash, 0.3s) was seen and the
board stayed responsive afterward** — this is the first upload of the full
bridge script that did not brick the board. This confirms the `@event.start`
fix works for the complete bridge, not just trivial snippets.

**Not yet confirmed: the actual stdin/stdout line protocol.** Tried sending
a plain-text `PING` via mBlock's own bottom-panel "Send" box (unchecked Hex
Send/Receive first) — produced **no new log activity at all**, not even an
echo of the sent bytes. This is inconclusive rather than a negative result:
that Send box most likely only functions in Live mode (talking to code
actively driven by the browser), not to a standalone program already
persisted and running via Upload mode — so it likely just doesn't apply
here, rather than proving stdin/stdout is broken.

**Next step to actually confirm the MCP bridge works end-to-end:** test with
this repo's real `SerialTransport` (`src/mbot2_mcp/transport.py`) against
whatever port the connection presents — ideally over USB
(`/dev/ttyUSB0`) if a cable is available, since that's a guaranteed classic
serial port `pyserial` can open directly. Bluetooth is a real open question
for this architecture: mBlock's browser connection uses **Web
Bluetooth (BLE/GATT)**, which is architecturally different from **classic
Bluetooth SPP** (the `/dev/rfcomm0`-style port `SerialTransport`/pyserial
expects, per `README.md`'s Bluetooth section). Whether the CyberPi exposes
classic SPP at all (pairable via the OS's normal Bluetooth settings,
independent of mBlock/mLink) has not been verified — if it only exposes
BLE/GATT, this repo's pyserial-based transport cannot talk to it over
Bluetooth without additional work (a BLE client library, not pyserial).

**Required fix for `mbot2_bridge.py` before any further upload attempt:**
1. Add `import event` and wrap the existing `main()` body in a function
   decorated `@event.start` (e.g. rename `main` to `on_start` or call the
   existing `main()` from inside an `@event.start`-decorated wrapper).
2. Re-check the module/API convention: the working example uses top-level
   `import mbot2` / `import mbuild` with calls like
   `mbuild.ultrasonic2.get(1)`, `mbot2.turn(90)`, `mbot2.forward(30)` —
   different from `mbot2_bridge.py`'s current `import cyberpi as cpi` +
   `getattr(cpi, "mbot2", None)` + `cpi.ultrasonic2`/`cpi.quad_rgb_sensor`
   attribute-access convention. Both conventions exist in Makeblock's
   ecosystem; this board's firmware has now only been confirmed to work
   with the former. The bridge's device calls should be re-verified against
   the confirmed-working convention rather than assumed.
3. Re-test incrementally (small marker-bearing snippets, as done here)
   before uploading the full bridge again.

## Part 7 — CONFIRMED: CyberPi's Bluetooth is BLE-only, not classic SPP

Checked `bluetoothctl devices` / `bluetoothctl info` directly against the
OS Bluetooth stack (BlueZ) while connected. The CyberPi appears as
`Makeblock_LEECE334319CF2` (`EC:E3:34:31:9C:F2`), address type **public**,
`Paired: no`, `Bonded: no`, and its only advertised GATT services are:

```
UUID: Generic Access Profile    (00001800-...)
UUID: Generic Attribute Profile (00001801-...)
UUID: Unknown                   (0000ffe1-...)
```

`0000ffe1` is the well-known "BLE-UART" characteristic used by cheap
transparent-serial-over-BLE modules (the HM-10-style FFE0 service / FFE1
characteristic pattern) — a GATT characteristic, not a classic RFCOMM
channel. For comparison, other paired devices on this same machine (e.g.
"Soundcore P3i", "bosi" headphones) explicitly advertise
`UUID: Serial Port (00001101-...)`, the actual classic Bluetooth SPP UUID —
CyberPi advertises **no such UUID**. `rfcomm` shows no bound channels and
no `/dev/rfcomm*` device exists.

**Conclusion: CyberPi's Bluetooth is BLE/GATT-only. It does not implement
classic Bluetooth SPP at all.** This is exactly why mBlock's browser
connects via Web Bluetooth (the only API that can reach it) and why the
wire protocol is wrapped in Makeblock's own binary framing (`f0`/`f3`
packets) — that framing is very likely their own chunking/flow-control
layer built on top of the BLE characteristic's small MTU, not an arbitrary
design choice.

**Impact on this repo:** `src/mbot2_mcp/transport.py`'s `SerialTransport`
is built on `pyserial`, which only understands classic serial ports
(`/dev/ttyUSB0`, `/dev/rfcomm0`, COM ports) — it has no concept of BLE GATT
characteristics and **cannot connect to this board over Bluetooth as
currently implemented**, regardless of anything on the CyberPi/firmware
side. `README.md`'s Bluetooth section (`/dev/rfcomm0`,
`/dev/tty.CyberPi-xxxx`, "just another serial port — zero code changes")
is **incorrect for this hardware** — that description matches classic
Bluetooth SPP devices, which this board is not. Supporting Bluetooth here
would require a BLE GATT client (e.g. Python's `bleak` library) written
against the `0000ffe0`/`0000ffe1`-style service, a real architecture
change, not a config tweak.

**Practical consequence right now:** the only way to verify (or use) this
repo's actual line protocol end-to-end is over **USB**
(`/dev/ttyUSB0`, plain serial, confirmed working pre-brick). Bluetooth
remains usable for uploading code via mBlock (that's what the browser is
already doing), but not for the MCP server's own `SerialTransport` until/
unless BLE support is added.

## Status at time of writing

Second CyberPi firmware reinstall in progress by the user. No further writes
to the device, serial port, mlink daemon, or mBlock browser tabs should
happen from this agent without explicit user go-ahead, regardless of what is
being uploaded.
