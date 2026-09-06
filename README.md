# mbot2-mcp — tiny MCP server for mBot2 / CyberPi (opencode)

Stdio MCP server. opencode spawns it, calls tools, server sends one-line
serial commands to the CyberPi bridge (`cyberpi/mbot2_bridge.py`).

```
opencode
  │ MCP (stdio)
  ▼
mbot2-mcp  (this repo: drive/stop/ultrasonic/line/gyro/led/beep)
  │ 1 line out / 1 line back, 115200 baud
  ▼
USB serial  ──or──  Bluetooth-serial (same serial port abstraction)
  ▼
CyberPi running mbot2_bridge.py  →  mBot2 chassis
```

No MQTT. No flashing of CyberOS (the bridge is a MicroPython `main.py`
upload, which coexists with CyberOS — unlike Arduino flashing, which wipes it).

## Docs (knowledge captured 2026-09-06, don't lose it)

- `docs/01-linux-setup.md` — mLink driver download (**<https://s.mblock.cc/download/mlink-deb>**,
  fetch in browser, `curl` only gets a JS landing page), install to
  `/usr/local/makeblock/mLink`, start (`mlink start`, port 55278), `dialout` group fix
- `docs/02-bridge-upload.md` — power on, Chrome upload of `cyberpi/mbot2_bridge.py`, verify `PING`
- `docs/03-opencode-mcp.md` — opencode config, 12 tools, calibration + fleet rollout
- `docs/04-troubleshooting.md` — every failure seen so far and its fix

## Quick start (no robot needed)

```bash
cd /home/cda/dev/mbot2-mcp
pip install -e .
MBOT2_MOCK=1 python -m mbot2_mcp.server   # runs, waits for MCP on stdio
```

Point opencode at it (`opencode-mcp.example.json`):

- single bot: `MBOT2_PORT=/dev/ttyUSB0`
- course fleet: `MBOT2_BOTS="A=/dev/ttyUSB0,B=/dev/ttyUSB1"`
- dev without hardware: `MBOT2_MOCK=1`

Real-port example for `~/.config/opencode/opencode.json`:

```json
{ "mcp": { "mbot2": {
  "type": "local",
  "command": ["python", "-m", "mbot2_mcp.server"],
  "enabled": true,
  "environment": { "MBOT2_BOTS": "A=/dev/ttyUSB0,B=/dev/ttyUSB1" }
} } }
```

## Tools

`list_robots ping drive stop forward ultrasonic line_sensor gyro battery set_led beep show_text`

## When do you need a real USB connection?

Short version: **everything except §3 works without the bot.**
You only need USB for first contact, calibration, and Bluetooth naming.

1. **Not needed — build & test in mock (now).**
   Install, `MBOT2_MOCK=1`, wire into opencode, call every tool.
   Mock returns `DIST 42.0`, `LINE 0 1 1 0`, etc. No cable touched.

2. **Needed once — upload the bridge (5 min with cable).**
   mBlock 5 → connect CyberPi via **USB** → Upload mode → paste
   `cyberpi/mbot2_bridge.py` as `main.py` → Upload. Bluetooth can't do
   this first upload reliably, and mBlock + MCP can't share the port —
   **quit mBlock after uploading**. I need you on this step only to press
   Upload and tell me the serial port name (`/dev/ttyUSB0`, `COM5`, …).
   Find it with: `python scripts/list_ports.py` before/after plugging in.

3. **Needed briefly — calibrate on the real chassis.**
   I can't guess these without the bot: motor polarity
   (`drive_power(l, -r)` sign in the bridge), speed→motion mapping,
   ultrasonic scaling, which quad-RGB index (`index=1`?) your sensor uses,
   gyro axes, battery range. Plan: USB connected, wheels off the ground,
   run `ping → beep → set_led → drive(30,30) → stop → ultrasonic` and
   adjust signs. ~10 min, one session.

4. **Optional — Bluetooth naming (only for untethered driving).**
   After §2–3 work over USB, pair the CyberPi/BT dongle per
   Makeblock's guide. It shows up as just another serial port
   (`/dev/rfcomm0`, `/dev/tty.CyberPi-xxxx`, `COM6`). Put that port in
   `MBOT2_BOTS` — zero code changes. Tell me the port name and I'll
   switch the config. Bluetooth is never required; USB always works.

5. **Course fleet — one USB pass per bot.**
   Label each bot (A/B/C/D), repeat §2 with that bot plugged in,
   record `A=<port>` mapping. After that everything is remote/config.

### Correction to the initial research

The `0xFF 0x55 GET/RUN` framing you quoted is the **mBot v1 (Arduino)**
protocol (`mBot-default-program.ino`, `SerialDevice.as`). mBot2's brain is
a **CyberPi running CyberOS** — its PC-live protocol is proprietary and
undocumented. Re-implementing it would be fragile. This repo instead uploads
a 150-line MicroPython bridge that speaks a trivial line protocol and calls
the documented on-device API (`cyberpi.mbot2.forward/drive_power/EM_stop`,
`ultrasonic2`, `quad_rgb_sensor`, `led`, `audio`, `display`). Same tiny MCP
surface you sketched, but on a supported path.
