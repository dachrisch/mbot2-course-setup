#!/usr/bin/env python3
"""Browser-free uploader for the CyberPi (mBot2 brain) over USB serial.

Thin CLI shim over cyberpi_mcp.protocol (the single source of truth for
the framing decoded from a captured mBlock IDE session, 2026-09-08; see
docs/06-usb-upload-protocol.md). No browser, no mLink needed — plain
pyserial writes to /dev/ttyUSB0.

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
from pathlib import Path

try:
    from cyberpi_mcp import protocol
except ImportError:  # running from a checkout without `pip install -e .`
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from cyberpi_mcp import protocol


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
    wire = protocol.pad_to_wire_size(code)
    if len(wire) != len(code):
        print(f"padded {len(wire) - len(code)} trailing newlines for %80==4 framing "
              f"({len(wire)} bytes on the wire)")
    print(f"uploading {args.file} ({len(wire)} bytes) to {args.port}")
    s = protocol.upload(args.port, wire, baud=args.baud, debug=args.debug)
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
