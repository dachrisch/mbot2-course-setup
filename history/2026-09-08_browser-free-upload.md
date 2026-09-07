# 2026-09-08 — direct programming path: stdin dead, UART alive, browser-free uploads work

## Summary

Goal (user): "re-iterate the direct programming path" — control the mBot2
from the Linux CLI without opening mBlock. End of night: **uploads run
from one terminal command** (`scripts/mbot_upload.py`), proven with two
brand-new programs (red LED, hi + cheering notes, both physically
confirmed). Full-duplex live steering is still out: USB stdin is dead,
and the community UART bridge needs hardware that doesn't exist.

## Part 1 — USB serial baseline (all read-only)

- `/dev/ttyUSB0` (CH340 `1a86:7523`) opens via `dialout`, but is 0 bytes
  across passive listen, Ctrl-C, Ctrl-A raw REPL, at 9600/57600/115200/
  230400 — before and after a USB power cycle. No MicroPython REPL.
- `ttyACM0` is the LG monitor (ignore). Port must be exclusive: an open
  mBlock tab keeps mLink's `serialPortChildProcess.js` polling and the
  port flaps with `multiple access` errors.
- User session predates the `dialout` fix again — `sg dialout -c` used
  throughout; mLink itself was also restarted at some point (new PID).

## Part 2 — stdin/stdout via marker probe

Uploaded `cyberpi/serial_probe.py` (1569 B, `@event.start`, heartbeat +
stdin echo) through the `upload-cyberpi` skill flow (user connects +
Upload mode; editor set via base64 + `setValue`; 1569 = 1569 byte check).
Result on plain serial, no browser/mLink:
- **stdout works**: `CLI-PROBE-7F3A9 heartbeat` received twice.
- **stdin dead**: `uselect.poll()` never fires (LF and CRLF sends, stable
  exclusive port). No `readline` data ever arrives.

## Part 3 — community bridge (gianpaj/makeblock) assessed, not adopted

- Their host control runs over a **second hardware UART** (`machine.UART`
  on GPIO TX=32/RX=25) via an extra 3.3 V adapter — i.e. they routed
  *around* dead USB stdin too. Confirms Part 2 rather than contradicting.
- Their own PINOUT.md marks those pins **stale**: the bare CyberPi has no
  pin header (USB-C, HOME, mBuild only). Wiring needs solder or mBuild
  GPIO mapping (unknown).
- Their `main.py` is bare top-level code with no `@event.start` — the
  exact shape that bricked this board twice. Never upload it verbatim.
- Probed anyway: `uart_probe.py` (Pin objects → red,
  `uart-fail:can't convert Pin to int`), then `uart_probe2.py` (int pins
  → green, `uart-int-ok write-int-ok`). So `machine.UART(2, tx=32,
  rx=25)` comes up and `machine`/`ujson` exist — the firmware side is
  ready if wires ever reach those pins.

## Part 4 — mLink is a dumb proxy; transport spike

`/usr/local/makeblock/mLink` (~15 KB Node): socket.io server on 55278
with six primitives (`getDevices`/`open`/`write`/`close`/`flush`/`drain`).
No upload intelligence — all framing lives in mBlock's web JS. Spike
(stdlib `urllib` Engine.IO-v3 polling, since modern socket.io clients
can't handshake with the 2018 server): `getDevices` listed ttyUSB0,
`open` + live `s2c_receive` telemetry (823 B of probe prints) + `close`,
all without a browser.

## Part 5 — framing captured and cracked

In-page WebSocket/XHR hook (via reload `initScript`) captured a full
upload (uart_probe2, 1924 B): 35 writes out, ~230 frames in. Decoded:
- `F3 cmd len16LE body ck F4`, `ck = sum(body) & 0xFF` (37/37 incl.
  board-computed acks), lock-step write→ack pacing.
- ping `F6` (echoed), exec snippets → `F3 05 {"ret":...}`, open
  `/flash/_xx_main.py` (staging slot), 80 B `0x4D` chunks + 4 B `0x01`
  final, post-reboot `PYB: fast reboot` + `F3 F5` hello.
- Chunk payloads verified 24/24 byte-identical to the file (djb2).
- Side discovery: the preamble runs
  `config.write_config("repl_enable", False)` — persisted. That flag is
  the likely reason raw REPL/stdin is dead; flipping it back is the top
  open lead (untried).
- Full spec: `docs/06-usb-upload-protocol.md`.

## Part 6 — `scripts/mbot_upload.py` + the 0x01 saga

Reimplementation (raw pyserial, builder verified byte-for-byte against
the capture) passed identical bytes first try — then hit the real rule:
- `0x01` with 47 B or 1 B payload → total silence, running program stops,
  no reboot; only a physical power cycle recovers (DTR resets don't).
  Failed 3 times, zero bricks (staging/finalize protects the live program).
- `0x01` with exactly the last 4 bytes → acked (twice, two files).
- Short (77 B) `0x4D` tail → also rejected.
- Working rule: data `[0, size-4)` in `0x4D` (80 B), `0x01` with exactly
  `file[size-4:size]`. Proven for `size % 80 == 4` only (1924, 804,
  1044); everything else is untested — pad sources with trailing comments
  to fit. Short-frame and `%80==0` shapes are open questions, do not try
  blind (hang risk, power-cycle recovery).
- Post-finalize doesn't always reboot by itself (browser flow did; two
  raw-serial runs needed a power cycle despite byte-perfect uploads).
  Trigger unknown; power cycle is the fallback.

## Proof runs (all physically confirmed by the user)

- `cyberpi/red_test.py` (804 B): red LED ring. New content, zero browser.
- `cyberpi/hi_cheer.py` (1044 B): cyan LEDs, "Hi!", "hello" voice preset,
  C5-E5-G5-C6 arpeggio, green + "Cheers!" — user: "it played hi and
  shows cheers".

## Files added

- `scripts/mbot_upload.py` — the uploader (`--expect MARKER` gate).
- `docs/06-usb-upload-protocol.md` — the spec.
- `cyberpi/serial_probe.py`, `uart_probe.py`, `uart_probe2.py`,
  `red_test.py`, `hi_cheer.py` — probes/demos, all `@event.start`.
- (`/tmp/opencode`: `probe_*.py`, `listen_*.py`, `spike_mlink*.py`,
  `ck_crack*.py` — scratch, not committed.)

## Commands

```bash
sg dialout -c "python3 scripts/mbot_upload.py cyberpi/<file>.py --expect <MARKER>"
wc -c cyberpi/<file>.py   # must satisfy size % 80 == 4 (pad to fit)
```

## Standing notes

- `@event.start` held through 6 uploads tonight (3 browser, 3 serial).
  Never upload bare-entry-point code; never Arduino-flash (wipes CyberOS).
- Never touch the mlink daemon during browser work; close the IDE tab
  before raw-serial use (port contention).
- Next leads, in value order: (1) `repl_enable=True` exec probe (may
  restore REPL/mpremote), (2) open-token constancy + `%80==0` edge,
  (3) auto-reboot finale for the uploader, (4) solder/mBuild wired UART.
