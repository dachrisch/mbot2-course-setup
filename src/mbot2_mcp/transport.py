"""Serial + mock transports. One line out, one line back."""

from __future__ import annotations

import os
import threading
import time

_BAUD = int(os.environ.get("MBOT2_BAUD", "115200"))
_TIMEOUT = float(os.environ.get("MBOT2_TIMEOUT", "2.0"))

_lock = threading.Lock()
_serials: dict[str, object] = {}
_transports: dict[str, "BaseTransport"] = {}


class BaseTransport:
    def command(self, line: str) -> str:
        raise NotImplementedError


class MockTransport(BaseTransport):
    """Deterministic fake robot so you can develop without USB/Bluetooth."""

    def __init__(self, name: str = "default"):
        self.name = name

    def command(self, line: str) -> str:
        cmd = line.strip().upper()
        if cmd == "PING":
            return "OK PONG"
        if cmd.startswith("DRIVE") or cmd in ("STOP",) or cmd.startswith("FORWARD") or cmd.startswith("BACKWARD"):
            return "OK"
        if cmd.startswith("LED") or cmd.startswith("BEEP") or cmd.startswith("TEXT"):
            return "OK"
        if cmd == "ULTRA?":
            return "DIST 42.0"
        if cmd == "LINE?":
            return "LINE 0 1 1 0"
        if cmd == "GYRO?":
            return "GYRO 0.0 0.0 0.0"
        if cmd == "BAT?":
            return "BAT 100"
        return f"OK mock:{line}"


class SerialTransport(BaseTransport):
    def __init__(self, port: str, baud: int = _BAUD):
        import serial  # imported lazily so mock mode needs no pyserial

        self.port = port
        self.ser = serial.Serial(port, baudrate=baud, timeout=_TIMEOUT, write_timeout=_TIMEOUT)

    def command(self, line: str) -> str:
        with _lock:
            assert hasattr(self.ser, "reset_input_buffer")
            self.ser.reset_input_buffer()  # type: ignore[attr-defined]
            self.ser.write((line.strip() + "\n").encode())  # type: ignore[attr-defined]
            self.ser.flush()  # type: ignore[attr-defined]
            deadline = time.time() + _TIMEOUT + 1.0
            buf = b""
            while time.time() < deadline:
                chunk = self.ser.readline()  # type: ignore[attr-defined]
                if chunk:
                    buf += chunk
                    text = buf.decode(errors="replace").strip()
                    if text:
                        return text
                else:
                    time.sleep(0.02)
            return "ERR timeout (is mbot2_bridge.py running on the CyberPi?)"


def get_transport(name: str, port: str) -> BaseTransport:
    if port == "mock":
        if name not in _transports:
            _transports[name] = MockTransport(name)
        return _transports[name]
    if name not in _transports:
        _transports[name] = SerialTransport(port)
    t = _transports[name]
    assert isinstance(t, SerialTransport)
    # Reopen if the configured port changed (multi-bot course setup).
    if t.port != port:
        try:
            t.ser.close()  # type: ignore[attr-defined]
        except Exception:
            pass
        _transports[name] = SerialTransport(port)
    return _transports[name]


def list_serial_ports() -> list[str]:
    try:
        from serial.tools import list_ports

        return [p.device for p in list_ports.comports()]
    except Exception:
        return []
