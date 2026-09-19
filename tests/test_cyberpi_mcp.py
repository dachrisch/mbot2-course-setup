"""Tests for the cyberpi-upload MCP (upload-only, browser-free).

Covers the byte-identical protocol builders (replay of the captured mBlock
session — PING/EXEC bytes, F3/F4 framing, open/data/final shapes), the
size%80==4 padding rule, the @event.start entry-point guard, and the
mock-mode tool behaviour (hardware-free dev).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cyberpi_mcp import protocol, config, server  # noqa: E402


def test_ping_frame_is_byte_identical_to_capture():
    assert protocol.PING == bytes(
        [0xF3, 0xF6, 0x03, 0x00, 0x0D, 0x00, 0x00, 0x0D, 0xF4])


def test_frame_checksums_body():
    body = [0x01, 0x02, 0x03]
    f = protocol.frame(0x4D, body)
    assert f[0] == 0xF3 and f[-1] == 0xF4
    assert f[1] == 0x4D
    assert f[2] | (f[3] << 8) == len(body)
    assert f[-2] == (sum(body) & 0xFF)


def test_build_data_final_uses_cmd_0x01_with_last_4_bytes():
    code = bytes(range(84))  # 84 % 80 == 4
    data_end = len(code) - 4
    final = protocol.build_data(data_end, code[data_end:], final=True)
    assert final[1] == 0x01
    assert code[data_end:] in final


def test_build_data_chunk_uses_cmd_0x4d():
    chunk = protocol.build_data(0, bytes(80))
    assert chunk[1] == 0x4D


def test_pad_to_wire_size_only_pads_to_mod80_eq_4():
    assert protocol.pad_to_wire_size(b"x" * 84) == b"x" * 84
    assert len(protocol.pad_to_wire_size(b"x" * 100)) % 80 == 4
    assert protocol.pad_to_wire_size(b"x" * 100)[:100] == b"x" * 100
    # padding is trailing newlines only (semantically null in Python)
    assert set(protocol.pad_to_wire_size(b"x" * 100)[100:]) == {ord("\n")}


def test_check_file_reports_event_start_guard(tmp_path):
    good = tmp_path / "good.py"
    good.write_text("import event\n@event.start\ndef on_start():\n    pass\n")
    assert json.loads(server.check_file(str(good)))["has_event_start"] is True
    bad = tmp_path / "bad.py"
    bad.write_text('print("hello")\n')
    res = json.loads(server.check_file(str(bad)))
    assert res["has_event_start"] is False
    assert "warn" in res


def test_check_file_reports_wire_size(tmp_path):
    f = tmp_path / "sized.py"
    f.write_bytes(b"x" * 100)
    res = json.loads(server.check_file(str(f)))
    assert res["bytes"] == 100
    assert res["wire_bytes"] % 80 == 4
    assert res["wire_bytes"] >= 100


def test_list_local_lists_cyberpi_files():
    rows = json.loads(server.list_local())
    names = [r["name"] for r in rows]
    assert "welcome_greeter.py" in names
    row = next(r for r in rows if r["name"] == "welcome_greeter.py")
    assert row["has_event_start"] is True


def test_mock_mode_upload_returns_fake_without_touching_serial(tmp_path, monkeypatch):
    monkeypatch.setenv("CYBERPI_MOCK", "1")
    f = tmp_path / "demo.py"
    f.write_text("import event\n@event.start\ndef on_start():\n    pass\n")
    res = json.loads(server.upload(str(f)))
    assert res["mode"] == "mock"
    assert res["wire_bytes"] % 80 == 4


def test_config_single_port_env(monkeypatch):
    monkeypatch.setenv("CYBERPI_MOCK", "")
    monkeypatch.setenv("CYBERPI_BOTS", "")
    monkeypatch.setenv("CYBERPI_PORT", "/dev/ttyUSB0")
    assert config.load_bots() == {"default": "/dev/ttyUSB0"}


def test_config_mock_without_port(monkeypatch):
    monkeypatch.setenv("CYBERPI_MOCK", "1")
    monkeypatch.setenv("CYBERPI_BOTS", "")
    monkeypatch.delenv("CYBERPI_PORT", raising=False)
    assert config.load_bots() == {"default": "mock"}
