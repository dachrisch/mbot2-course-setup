#!/usr/bin/env python3
"""Browser-free uploader for the CyberPi (mBot2 brain) over USB serial.

Replays the upload protocol decoded from a captured mBlock IDE session
(2026-09-08; see docs + history). No browser, no mLink needed — plain
pyserial writes to /dev/ttyUSB0.

Frame format (all numbers single bytes, LE where noted):
    F3 cmd len_lo len_hi body... ck F4
    len = len(body); ck = sum(body) & 0xFF   (verified 37/37 frames)

Sequence for a file upload:
    ping, exec, exec, ping, exec, exec   (preamble, static boilerplate)
    open(/flash/_xx_main.py, size)       (staging slot; main.py untouched
                                          until finalize — a failed upload
                                          leaves the board's program intact)
    data chunks (80B) + final short chunk (remainder)
    ping, exec, exec                      (postamble; board reboots,
                                          prints "PYB: fast reboot", hello)

Data-chunk body: 01 00 5E 02 <paylen+4 LE16> <offset LE32> <payload>
Open body:       01 00 5E 01 1B 00 00 <size LE32> <token 4B> <path>
  (token A0 AA C1 3E + "1B 00 00" replayed verbatim from capture;
   if the board ever rejects open, the token may be session-specific —
   the error message says so explicitly.)

Acks (lock-step, one per write):
    ping -> identical echo frame
    exec -> F3 05 ... {"ret":...}
    open/chunk/final -> F3 FA ... ack
Board stdout (prints, REPL banner, reboot chatter) interleaves on the
same wire as plain text; the reader skips non-F3 bytes when framing.

Usage:
    python3 scripts/mbot_upload.py cyberpi/uart_probe2.py [--expect MARKER]
    (needs dialout: sg dialout -c "..." if your session lacks the group)

Framing constraint: the board only accepts files with size % 80 == 4
(short tails and non-4B finals are silently rejected and can hang the
board until power-cycled). The uploader pads with trailing newlines
(semantically null in Python) to fit — the file on disk is untouched.
"""

import argparse
import sys
import time

import serial

F3, F4 = 0xF3, 0xF4
PATH = b"/flash/_xx_main.py"
CHUNK = 80

PING = bytes([F3, 0xF6, 0x03, 0x00, 0x0D, 0x00, 0x00, 0x0D, F4])
EXEC1 = bytes([
    0xF3, 0x20, 0x2D, 0x00, 0x28, 0x04, 0x00, 0x00, 0x27, 0x00,
    *b"try:\n    import config\nexcept:\n    pass", 0xB5, F4])
EXEC2 = bytes([
    0xF3, 0x3C, 0x49, 0x00, 0x28, 0x04, 0x00, 0x00, 0x43, 0x00,
    *b'try:\n    config.write_config("repl_enable", False)\nexcept:\n    pass',
    0x89, F4])
OPEN_TOKEN = bytes([0xA0, 0xAA, 0xC1, 0x3E])


def frame(cmd, body):
    assert len(body) < 65536
    f = bytes([F3, cmd, len(body) & 0xFF, (len(body) >> 8) & 0xFF]) + bytes(body)
    return f + bytes([sum(body) & 0xFF, F4])


def build_open(code):
    body = (bytes([0x01, 0x00, 0x5E, 0x01, 0x1B, 0x00, 0x00])
            + len(code).to_bytes(4, "little") + OPEN_TOKEN + PATH)
    return frame(0x14, body)


def build_data(offset, payload, final=False):
    # cmd 0x4D = data (80B chunks AND short tail chunks), cmd 0x01 =
    # finalize carrying exactly the last 4 file bytes. sublen covers
    # offset(4) + payload in both cases (0x54/0x08 in the capture).
    sublen = len(payload) + 4
    body = (bytes([0x01, 0x00, 0x5E, 0x02])
            + sublen.to_bytes(2, "little")
            + offset.to_bytes(4, "little") + bytes(payload))
    return frame(0x01 if final else 0x4D, body)


def read_frame(s, deadline, debug=False):
    """Scan for next F3..F4 frame; skip interleaved plain-text chatter."""
    hdr = None
    text = bytearray()
    while time.time() < deadline:
        try:
            b = s.read(1)
        except Exception:
            # transient USB drop (board reboot / re-enumeration):
            # treat as silence, let the transact timeout drive retries
            time.sleep(0.2)
            continue
        if not b:
            continue
        b = b[0]
        if hdr is None:
            if b == F3:
                if debug and text:
                    print(f"    rx text: {bytes(text)!r}")
                    text = bytearray()
                hdr = [b]
            elif debug:
                text.append(b)
                if len(text) >= 300:
                    print(f"    rx text: {bytes(text)!r}")
                    text = bytearray()
            continue
        hdr.append(b)
        if len(hdr) == 4:
            body_len = hdr[2] | (hdr[3] << 8)
            if body_len > 4096:  # implausible -> resync
                hdr = [x for x in hdr[1:] if x == F3] or None
                if hdr == []:
                    hdr = None
                continue
        if len(hdr) >= 4:
            body_len = hdr[2] | (hdr[3] << 8)
            if len(hdr) == 4 + body_len + 2:
                cmd, body, ck, tail = hdr[1], hdr[4:-2], hdr[-2], hdr[-1]
                if tail != F4 or (sum(body) & 0xFF) != ck:
                    if debug:
                        print(f"    rx bad frame cmd=0x{cmd:02x} "
                              f"len={len(hdr)}")
                    hdr = None  # bad frame -> resync
                    continue
                if debug:
                    print(f"    rx frame cmd=0x{cmd:02x} "
                          f"body={bytes(body)[:60]!r}")
                return cmd, bytes(body)
    return None


def transact(s, data, expect, label, timeout=3.0, retries=3, debug=False):
    if debug:
        print(f"    tx {len(data)}B: {data[:24].hex()}...{data[-4:].hex()}")
    for attempt in range(retries):
        s.write(data)
        s.flush()
        deadline = time.time() + timeout
        while time.time() < deadline:
            fr = read_frame(s, deadline, debug=debug)
            if fr is None:
                break
            if fr[0] in expect:
                print(f"  {label}: ack cmd=0x{fr[0]:02x} "
                      f"(attempt {attempt + 1})")
                return fr
            if debug:
                print(f"  {label}: ignoring cmd=0x{fr[0]:02x}")
        print(f"  {label}: no ack, retrying ({attempt + 1}/{retries})")
    raise RuntimeError(f"no ack for {label} after {retries} attempts")


def upload(port, code, verbose=True, debug=False):
    s = serial.Serial(port, 115200, timeout=0.2)
    time.sleep(3.0)  # opening the port resets the board; let it boot
    s.reset_input_buffer()
    log = print if verbose else (lambda *a: None)

    for i, f in enumerate([PING, EXEC1, EXEC2, PING, EXEC1, EXEC2]):
        transact(s, f, {0xF6} if f == PING else {0x05}, f"pre[{i}]",
                 debug=debug)
    log("preamble done")

    transact(s, build_open(code), {0x05, 0xFA}, "open", debug=debug)
    nfull = (len(code) - 4) // CHUNK
    log(f"open ok, {len(code)} bytes: {nfull}x80B 0x4D + tail + 4B 0x01")
    assert len(code) > 4, "file too small for 4-byte-final split"
    data_end = len(code) - 4
    off = 0
    while off < data_end:
        chunk = code[off:off + CHUNK]
        if off + len(chunk) > data_end:
            chunk = code[off:data_end]  # clamp: 0x01 always gets last 4B
        transact(s, build_data(off, chunk), {0xFA}, f"chunk@{off}",
                 debug=debug)
        off += len(chunk)
    assert off == data_end, (off, data_end)
    transact(s, build_data(off, code[off:], final=True), {0xFA},
             f"final@{off}", debug=debug)
    log("data done")

    for i, f in enumerate([PING, EXEC1, EXEC2]):
        transact(s, f, {0xF6} if f == PING else {0x05}, f"post[{i}]",
                 debug=debug)
    log("postamble done; waiting for reboot + program output...")
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--expect", default=None,
                    help="marker text proving the new program runs")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--debug", action="store_true",
                    help="dump every received frame")
    args = ap.parse_args()

    with open(args.file, "rb") as fh:
        code = fh.read()
    pad = (4 - len(code) % 80) % 80
    if pad:
        code = code + b"\n" * pad
        print(f"padded {pad} trailing newlines for %80==4 framing "
              f"({len(code)} bytes on the wire)")
    print(f"uploading {args.file} ({len(code)} bytes) to {args.port}")
    s = upload(args.port, code, debug=args.debug)
    if args.expect:
        needle = args.expect.encode()
        buf = bytearray()
        t0 = time.time()
        while time.time() - t0 < 20:
            buf += s.read(256)
            if needle in buf:
                print(f"SUCCESS: marker {args.expect!r} seen on serial")
                s.close()
                return 0
        print(f"FAIL: marker {args.expect!r} not seen; got {len(buf)} bytes:")
        print(repr(bytes(buf)[:500]))
        s.close()
        return 1
    s.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
