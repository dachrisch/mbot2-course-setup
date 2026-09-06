"""Robot/port resolution from environment.

Single bot:
    MBOT2_PORT=/dev/ttyUSB0  (or COM5 on Windows, /dev/tty.CyberPi-xxx on macOS BT)

Multiple bots (your course setup):
    MBOT2_BOTS="A=/dev/ttyUSB0,B=/dev/ttyUSB1,C=/dev/ttyUSB2"

Mock mode (no hardware, develop anywhere):
    MBOT2_MOCK=1
"""

from __future__ import annotations

import os


def load_robots() -> dict[str, str]:
    if os.environ.get("MBOT2_MOCK", "").strip().lower() in ("1", "true", "yes", "on"):
        bots = os.environ.get("MBOT2_BOTS", "").strip()
        if bots:
            names = [p.split("=", 1)[0].strip() or "default" for p in bots.split(",")]
            return {n: "mock" for n in names}
        return {"default": "mock"}

    bots = os.environ.get("MBOT2_BOTS", "").strip()
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

    port = os.environ.get("MBOT2_PORT", "").strip()
    if port:
        return {"default": port}
    # No port configured yet -> safe mock so opencode still starts.
    return {"default": "mock"}


def active_robot_names() -> list[str]:
    return sorted(load_robots())
