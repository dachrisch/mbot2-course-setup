"""MCP server for CyberPi uploads — stdio transport for opencode.

Upload-only: wraps the browser-free USB upload protocol
(cyberpi_mcp.protocol, decoded 2026-09-08) as MCP tools. No browser,
no mLink, no live drive/sensor control (USB stdin is dead on this board;
see docs/06-usb-upload-protocol.md and history/2026-09-08_browser-free-upload.md).
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

try:  # mcp 2.x: FastMCP renamed to MCPServer
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from . import config
from . import protocol

log = logging.getLogger("cyberpi-upload")

mcp = _Server("cyberpi-upload")

REPO_ROOT = Path(__file__).resolve().parents[2]

EVENT_START_WARNING = (
    "missing 'import event' / '@event.start': the CyberPi runtime requires "
    "the entry point via @event.start — bare top-level code or "
    "if __name__ == '__main__' has bricked this board twice "
    "(boot logo then dark, firmware reinstall). Confirm before uploading."
)


def _file_report(path: Path) -> dict:
    code = path.read_bytes()
    wire = protocol.pad_to_wire_size(code)
    text = code.decode("utf-8", errors="replace")
    has_event = "@event.start" in text and "import event" in text
    report = {
        "path": str(path),
        "bytes": len(code),
        "wire_bytes": len(wire),
        "padded_newlines": len(wire) - len(code),
        "has_event_start": has_event,
    }
    if not has_event:
        report["warn"] = EVENT_START_WARNING
    return report


@mcp.tool()
def check_file(path: str = "cyberpi/welcome_greeter.py") -> str:
    """Pre-upload check: byte size, wire size (%80==4), @event.start guard.

    Warns (does not block) when the entry-point guard is missing.
    """
    p = Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / p
    if not p.is_file():
        return json.dumps({"ok": False, "error": f"not a file: {path}"})
    report = _file_report(p)
    report["ok"] = True
    return json.dumps(report, indent=2)


@mcp.tool()
def list_local() -> str:
    """List cyberpi/*.py sources with size + @event.start status."""
    rows = []
    for p in sorted((REPO_ROOT / "cyberpi").glob("*.py")):
        try:
            rows.append(_file_report(p) | {"name": p.name})
        except OSError as exc:
            rows.append({"name": p.name, "ok": False, "error": str(exc)})
    return json.dumps(rows, indent=2)


@mcp.tool()
def upload(path: str = "cyberpi/welcome_greeter.py", board: str = "default",
           expect_marker: str | None = None) -> str:
    """Upload a MicroPython file to the CyberPi over USB serial.

    Needs exclusive port access: close any mBlock IDE tab first (it polls
    the port via mLink). After a successful finalize the board does not
    always reboot by itself — power-cycle it if no marker appears within
    ~20 s. A failed upload leaves the live program intact (staging slot).
    """
    p = Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / p
    if not p.is_file():
        return json.dumps({"ok": False, "error": f"not a file: {path}"})
    try:
        port = config.resolve_port(board)
    except ValueError as exc:
        return json.dumps({"ok": False, "error": str(exc)})

    report = _file_report(p)
    if port == "mock":
        return json.dumps({
            "ok": True, "mode": "mock", "port": port,
            "path": str(p), "bytes": report["bytes"],
            "wire_bytes": report["wire_bytes"],
            "has_event_start": report["has_event_start"],
        }, indent=2)

    code = protocol.pad_to_wire_size(p.read_bytes())
    if len(code) != report["wire_bytes"]:
        return json.dumps({"ok": False,
                           "error": "wire-size mismatch, aborting"})
    try:
        s = protocol.upload(port, code, verbose=False)
    except Exception as exc:
        log.exception("upload failed")
        return json.dumps({"ok": False, "port": port,
                           "error": f"{type(exc).__name__}: {exc}",
                           "hint": "close any mBlock tab (port contention); "
                                   "`sg dialout -c ...` if session predates "
                                   "the dialout fix."})
    marker_seen = False
    if expect_marker:
        needle = expect_marker.encode()
        buf = bytearray()
        t0 = time.time()
        while time.time() - t0 < 20:
            try:
                buf += s.read(256)
            except Exception:
                time.sleep(0.2)
                continue
            if needle in buf:
                marker_seen = True
                break
    try:
        s.close()
    except Exception:
        pass
    out = {"ok": True, "mode": "serial", "port": port, "path": str(p),
           "bytes": report["bytes"], "wire_bytes": report["wire_bytes"],
           "has_event_start": report["has_event_start"],
           "power_cycle_hint": expect_marker is not None and not marker_seen}
    if expect_marker:
        out["expect_marker"] = expect_marker
        out["marker_seen"] = marker_seen
    if not report["has_event_start"]:
        out["warn"] = EVENT_START_WARNING
    return json.dumps(out, indent=2)


@mcp.tool()
def listen(board: str = "default", seconds: int = 20,
           expect: str | None = None) -> str:
    """Listen on the serial port for program output / a marker string.

    Skips the upload-protocol framing; plain-text prints show through.
    Read-only: never writes to the board.
    """
    try:
        port = config.resolve_port(board)
    except ValueError as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    if port == "mock":
        return json.dumps({"ok": True, "mode": "mock",
                           "tail": "CLI-PROBE mock heartbeat"}, indent=2)
    try:
        import serial
        s = serial.Serial(port, 115200, timeout=0.2)
        time.sleep(3.0)  # open resets the board; let it boot
        s.reset_input_buffer()
        buf = bytearray()
        t0 = time.time()
        while time.time() - t0 < max(1, min(120, int(seconds))):
            try:
                buf += s.read(256)
            except Exception:
                time.sleep(0.2)
                continue
            if expect and expect.encode() in buf:
                break
        s.close()
    except Exception as exc:
        return json.dumps({"ok": False, "port": port,
                           "error": f"{type(exc).__name__}: {exc}"})
    tail = bytes(buf[-500:]).decode("utf-8", errors="replace")
    return json.dumps({"ok": True, "mode": "serial", "port": port,
                       "bytes": len(buf), "tail": tail,
                       "marker_seen": bool(expect and expect.encode() in buf)},
                      indent=2)


def main() -> None:
    if os.environ.get("CYBERPI_MOCK", "").strip().lower() in (
            "1", "true", "yes", "on"):
        log.warning("CYBERPI_MOCK=1: hardware-free mock mode")
    mcp.run()


if __name__ == "__main__":
    main()
