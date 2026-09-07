# USB upload protocol (decoded 2026-09-08 — browser-free uploads work)

Source: a full socket.io capture of one mBlock IDE upload
(`cyberpi/uart_probe2.py`, 1924 bytes) via an in-page WebSocket/XHR hook,
plus a from-scratch Python reimplementation (`scripts/mbot_upload.py`).
Proven end to end 2026-09-08: brand-new content (`cyberpi/red_test.py`,
804 bytes) uploaded over raw serial, board rebooted, red LED confirmed
by the user, program marker on the wire.

## Transport

- Plain serial does it all: `/dev/ttyUSB0`, 115200 8N1. mLink is only a
  socket.io proxy (`getDevices`/`open`/`write`/`close` on port 55278) with
  no upload intelligence — the framing below can go straight on the wire.
- Opening the port resets the board (DTR). Wait ~3 s + drain before
  starting. The uploader needs **exclusive** port access: an open mBlock
  tab keeps mLink's `serialPortChildProcess.js` polling and causes
  `multiple access on port` flakiness. (`sg dialout -c ...` if the shell
  session predates the `dialout` group fix.)

## Frame format

```
F3 cmd len_lo len_hi body... ck F4
len = len(body);  ck = sum(body) & 0xFF   (verified 37/37 frames,
including board-computed acks)
```

Non-F3 bytes on the wire are the running program's plain-text stdout
(prints, REPL banner, `PYB: fast reboot`) — the reader must skip them
when framing.

## Commands (host -> board)

| cmd  | name  | body layout | board reply |
|------|-------|-------------|-------------|
| `F6` | ping  | `0D 00 00` | byte-identical echo |
| `20`/`3C` | exec snippet | `28 04 00 00 <len LE16> <ASCII>` | `F3 05 ... {"ret":...}` |
| `14` | file open | `01 00 5E 01 1B 00 00 <size LE32> <token 4B> <path>` | `F3 FA` ack |
| `4D` | data chunk | `01 00 5E 02 <paylen+4 LE16> <offset LE32> <80 B>` | `F3 FA` ack |
| `01` | finalize | **exactly the last 4 file bytes** (same layout, short payload) | `F3 FA` ack, then reboot |

Proven limits (2026-09-08, three incidents):
- A `0x01` frame with any payload length other than 4 (tried 47 B and
  1 B) gets **no ack at all** — total wire silence, and the board stops
  its running program without rebooting. Only a physical power cycle
  recovers it (DTR resets don't). Failed this way 3 times, no bricks:
  the live program is untouched until a successful finalize.
- A short (77 B) `0x4D` tail chunk is likewise rejected with silence.
- Consequence: the uploader only handles files with `size % 80 == 4`
  (pad sources with trailing comment lines to fit). All other shapes —
  short `0x4D`, non-4B `0x01`, `size % 80 == 0` — are untested guesses,
  do not try them blind.
- After a *successful* finalize the board does not always reboot by
  itself (browser flow did; raw-serial flow twice needed a power cycle
  before the new program booted — bytes verified correct on the wire both
  times). Reboot trigger unknown; power cycle is the reliable fallback.

Observed constants (replayed verbatim by the uploader):
- exec snippets: `try:\n    import config\nexcept:\n    pass` and
  `try:\n    config.write_config("repl_enable", False)\nexcept:\n    pass`
  (note: the upload flow **persists `repl_enable=False`** — this is why
  raw REPL/stdin is silent on this board; re-enabling it is an open lead,
  not yet tried)
- open path `/flash/_xx_main.py` (staging slot — the live program is
  untouched until finalize, so a failed upload doesn't brick the board),
  size = full file length LE32, token `A0 AA C1 3E`, prefix `1B 00 00`
- `5E 01` (open) / `5E 02` (data) / `5E F0` (in acks) look like channel ids

## Sequence (35 writes for the 1924-byte capture)

```
ping, exec, exec, ping, exec, exec      # preamble (two passes)
open(size=1924)
24 x 80-byte chunks @ offsets 0..1840
final: 4 bytes @ offset 1920           # 1920 + 4 = 1924 total
ping, exec, exec                        # postamble
# board: "PYB: fast reboot", F3 F5 hello, then the new program's prints
```

Pacing is lock-step: send one frame, wait for its ack (3 s timeout,
3 retries in the uploader), then send the next.

Rule of thumb for new files: data region `[0, size-4)` in `0x4D`
frames (80 B each), then `0x01` with exactly `file[size-4:size]`.
Proven with `uart_probe2.py` (1924 B, identical bytes), `red_test.py
(804 B, new content, red LED confirmed)`, `hi_cheer.py` (1044 B, new
content, hi + cheers confirmed) — all `% 80 == 4` by construction
(padded with trailing comments where needed).

## Open questions (do not guess — capture again)

- Is the 4-byte open token constant across sessions/files, or per-upload?
  (Same token replayed across 5 uploads in one session — always accepted.)
- `size % 80 == 0` files: is the final frame sent empty or skipped?
- Meaning of `1B 00 00` (open) and the `F0 ... F7` frames (Live-mode
  polling, unrelated to upload).
- Does setting `repl_enable=True` via an exec frame restore raw REPL?
  (Would reopen the mpremote/ampy path — high value, untested.)
- What reboots the board after finalize in the browser flow? Raw-serial
  uploads twice needed a power cycle; the trigger is unknown.

## Tool

`scripts/mbot_upload.py cyberpi/<file>.py [--expect MARKER]` — usage in
its docstring. Hard requirement: file size `% 80 == 4` (pad with trailing
comments); the uploader asserts nothing, the board just goes silent on
other shapes. Needs exclusive port access (close any mBlock tab first)
and `dialout` (`sg dialout -c ...` if needed). After a successful upload,
if no marker appears within ~20 s, power-cycle the board before assuming
failure.
