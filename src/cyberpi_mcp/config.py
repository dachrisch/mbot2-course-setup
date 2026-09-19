"""Board/port resolution from environment.

Single board:
    CYBERPI_PORT=/dev/ttyUSB0

Multiple boards (course fleet, one entry per serial port):
    CYBERPI_BOTS="A=/dev/ttyUSB0,B=/dev/ttyUSB1"

Mock mode (no hardware, develop anywhere):
    CYBERPI_MOCK=1
"""

from __future__ import annotations

import os


def _mock_requested() -> bool:
    return os.environ.get("CYBERPI_MOCK", "").strip().lower() in (
        "1", "true", "yes", "on")


def load_bots() -> dict[str, str]:
    if _mock_requested():
        bots = os.environ.get("CYBERPI_BOTS", "").strip()
        if bots:
            names = [p.split("=", 1)[0].strip() or "default"
                     for p in bots.split(",")]
            return {n: "mock" for n in names}
        return {"default": "mock"}

    bots = os.environ.get("CYBERPI_BOTS", "").strip()
    if bots:
        out: dict[str, str] = {}
        for part in bots.split(","):
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                name, port = part.split("=", 1)
                out[name.strip() or "default"] = port.strip()
            else:
                out["default"] = part
        if out:
            return out

    port = os.environ.get("CYBERPI_PORT", "").strip()
    if port:
        return {"default": port}
    # No port configured yet -> safe mock so the MCP server still starts.
    return {"default": "mock"}


def resolve_port(board: str = "default") -> str:
    """Resolve a board id to a serial port (or 'mock')."""
    bots = load_bots()
    if board not in bots:
        if len(bots) == 1:
            board = next(iter(bots))
        else:
            raise ValueError(
                f"unknown board {board!r}; known: {sorted(bots)} "
                f"(set CYBERPI_BOTS, e.g. A=/dev/ttyUSB0,B=/dev/ttyUSB1)")
    return bots[board]
