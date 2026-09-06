"""MCP server for mBot2 / CyberPi — stdio transport for opencode."""

from __future__ import annotations

import json
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from .config import load_robots, active_robot_names
from .transport import get_transport, MockTransport

log = logging.getLogger("mbot2-mcp")

mcp = FastMCP("mbot2")


def _t(robot: str):
    """Resolve transport for a robot id (falls back to default/mock)."""
    robots = load_robots()
    if robot not in robots:
        # single-bot setups call tools without a robot id — use default
        if len(robots) == 1:
            robot = next(iter(robots))
        else:
            raise ValueError(
                f"unknown robot {robot!r}; known: {sorted(robots)} "
                f"(set MBOT2_BOTS, e.g. A=/dev/ttyUSB0,B=/dev/ttyUSB1)"
            )
    return get_transport(robot, robots[robot])


@mcp.tool()
def list_robots() -> str:
    """List configured mBot2 robots and their serial ports / mode."""
    robots = load_robots()
    rows = []
    for name in sorted(robots):
        t = get_transport(name, robots[name])
        kind = "mock" if isinstance(t, MockTransport) else "serial"
        rows.append({"robot": name, "port": robots[name], "mode": kind})
    return json.dumps(rows, indent=2)


@mcp.tool()
def ping(robot: str = "default") -> str:
    """Check that a robot bridge is alive. Returns 'OK PONG' on real hardware."""
    return _t(robot).command("PING")


@mcp.tool()
def drive(robot: str = "default", left: int = 0, right: int = 0) -> str:
    """Drive motors directly. left/right in -100..100 (negative = backward)."""
    left = max(-100, min(100, int(left)))
    right = max(-100, min(100, int(right)))
    return _t(robot).command(f"DRIVE {left} {right}")


@mcp.tool()
def stop(robot: str = "default") -> str:
    """Stop both motors."""
    return _t(robot).command("STOP")


@mcp.tool()
def forward(robot: str = "default", speed: int = 50, secs: float = 0) -> str:
    """Drive forward at speed 0..100, optionally for secs seconds."""
    speed = max(0, min(100, int(speed)))
    return _t(robot).command(f"FORWARD {speed} {secs}")


@mcp.tool()
def ultrasonic(robot: str = "default") -> str:
    """Read ultrasonic distance in cm. Returns e.g. 'DIST 23.4'."""
    return _t(robot).command("ULTRA?")


@mcp.tool()
def line_sensor(robot: str = "default") -> str:
    """Read 4-channel line follower. Returns e.g. 'LINE 1 0 0 1'."""
    return _t(robot).command("LINE?")


@mcp.tool()
def gyro(robot: str = "default") -> str:
    """Read CyberPi IMU. Returns e.g. 'GYRO 0.1 0.2 90.5' (roll pitch yaw)."""
    return _t(robot).command("GYRO?")


@mcp.tool()
def battery(robot: str = "default") -> str:
    """Read battery level. Returns e.g. 'BAT 87'."""
    return _t(robot).command("BAT?")


@mcp.tool()
def set_led(robot: str = "default", r: int = 0, g: int = 0, b: int = 255, id: str = "all") -> str:
    """Set CyberPi LEDs. r/g/b 0..255, id 'all' or 1..5."""
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return _t(robot).command(f"LED {r} {g} {b} {id}")


@mcp.tool()
def beep(robot: str = "default", freq: int = 880, ms: int = 200) -> str:
    """Beep the buzzer. freq in Hz, ms duration."""
    return _t(robot).command(f"BEEP {int(freq)} {int(ms)}")


@mcp.tool()
def show_text(robot: str = "default", text: str = "hi") -> str:
    """Show short text on the CyberPi screen."""
    safe = str(text).replace("\n", " ")[:48]
    return _t(robot).command(f"TEXT {safe}")


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("MBOT2_LOG", "WARNING"),
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    log.warning("robots: %s (mock=%s)", active_robot_names(), os.environ.get("MBOT2_MOCK", ""))
    mcp.run()


if __name__ == "__main__":
    main()
