# AGENTS.md — `tests/`

One file, `test_cyberpi_mcp.py`: 11 **hardware-free** tests for the upload MCP
(`../src/cyberpi_mcp/`). No board, serial port, or browser is needed to run it.

## Rules

- Tests prepend `../src` to `sys.path` at import time so they run from a plain
  checkout without `pip install -e .`. Keep that mechanism; don't switch to an
  install-dependent import.
- Use `CYBERPI_MOCK=1` / `monkeypatch` for upload and config behavior. Never
  add a test that requires a real serial device — the suite must stay runnable
  anywhere (see `../src/AGENTS.md` for the mock contract).
- The PING/frame byte-identity assertions are regression guards against the
  captured mBlock session. Treat those magic bytes as spec, not cleanup
  targets.
- `pyproject.toml` sets `[tool.pytest.ini_options] testpaths = ["tests"]`, so a
  bare `pytest` from the repo root finds the suite.

## Commands

```bash
python3 -m pytest tests/ -q    # 11 passed (verified); add -q -vv only when debugging
```

A pass here covers protocol framing, `%80==4` padding, the `@event.start`
guard, `list_local`/`check_file`, and mock-mode upload/config. It does **not**
prove an upload worked — that still needs a powered board and physical
confirmation (see [../cyberpi/AGENTS.md](../cyberpi/AGENTS.md)).
