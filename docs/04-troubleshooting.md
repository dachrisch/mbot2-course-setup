# Troubleshooting (symptoms seen 2026-09-06)

| Symptom | Cause | Fix |
|---|---|---|
| `Permission denied: '/dev/ttyUSB0'` | user not in `dialout` (`ls -l` shows `root:dialout`, mode 660) | `sudo usermod -aG dialout $USER`, log out/in; or `sg dialout -c "..."` |
| Port opens, `PING` → `ERR timeout`, raw read silent | bridge not uploaded yet, or bot powered off | power switch ON (sensor LEDs lit) → upload `cyberpi/mbot2_bridge.py` via Chrome (§2) → close tab → retry |
| `Device or resource busy` opening port | mBlock tab / mLink / another process holds it | close browser tab or Disconnect in IDE; `fuser /dev/ttyUSB0` to find holder |
| `curl` of mLink URL gives 5 KB HTML | URL serves a JS countdown page, not the file | download the .deb **in the browser** from <https://s.mblock.cc/download/mlink-deb> |
| `dpkg: ... is not a Debian format archive` | you installed the HTML page saved as `.deb` | re-download properly (check with `file xxx.deb` → must say `Debian binary package`) |
| `ModuleNotFoundError: mcp.server.fastmcp` | `mcp>=2` renamed FastMCP → MCPServer | repo pins `mcp>=1,<2` in `pyproject.toml`; `pip install -e .` again |
| `ModuleNotFoundError: mbot2_mcp` under `sudo` | `pip install -e .` was user-local; root env lacks it | don't use sudo — fix `dialout` membership instead |
| Only `/dev/ttyS*` listed, no `ttyUSB*` | cable unplugged, charge-only cable, or bot off | use a data cable, replug, compare `list_ports.py` before/after |
| One wheel backward on `drive(30,30)` | motor polarity assumption wrong for your chassis | flip that side's sign in bridge `DRIVE` handler, re-upload |
| `LINE?` always `0 0 0 0` | wrong `quad_rgb_sensor` index or sensor unplugged | check mBuild plug, try `index=2` in bridge, re-upload |

Raw-port diagnosis snippet (bypasses the MCP, talks serial directly):

```bash
sg dialout -c "python3 -c \"
import serial, time
s = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.5)
time.sleep(1); s.reset_input_buffer()
s.write(b'PING\n'); s.flush()
t0=time.time()
while time.time()-t0 < 3:
    line = s.readline()
    if line: print(repr(line))
\""
```
