# opencode wiring + live calibration

## 1. Install the server

```bash
cd /home/cda/dev/mbot2-mcp
pip install -e .
```

## 2. Configure opencode

Single bot (`~/.config/opencode/opencode.json`):

```json
{ "mcp": { "mbot2": {
  "type": "local",
  "command": ["python", "-m", "mbot2_mcp.server"],
  "enabled": true,
  "environment": { "MBOT2_PORT": "/dev/ttyUSB0" }
} } }
```

Course fleet (multiple paired robots — one entry per serial port):

```json
{ "mcp": { "mbot2": {
  "type": "local",
  "command": ["python", "-m", "mbot2_mcp.server"],
  "enabled": true,
  "environment": { "MBOT2_BOTS": "A=/dev/ttyUSB0,B=/dev/ttyUSB1" }
} } }
```

Hardware-free dev (no USB/Bluetooth needed):

```json
{ "environment": { "MBOT2_MOCK": "1" } }
```

Mock returns deterministic fakes (`DIST 42.0`, `LINE 0 1 1 0`, …) so every
tool works without a robot. Env knobs: `MBOT2_PORT`, `MBOT2_BOTS`,
`MBOT2_MOCK=1`, `MBOT2_BAUD` (default 115200), `MBOT2_TIMEOUT` (default 2.0s).

## 3. Tools (12)

`list_robots ping drive stop forward ultrasonic line_sensor gyro battery set_led beep show_text`
— see `server.py`. `drive(left, right)` takes −100..100 per side.

## 4. Live calibration (needs the bot, wheels off the ground, ~10 min)

Run in order; fix what disagrees. Record results in `04-calibration-log.md`.

1. `ping` → expect `OK PONG`.
2. `beep` + `set_led(0,0,255)` → buzzer sounds, LEDs blue (proves TX path).
3. `drive(robot, 30, 30)` → **both wheels forward?** If a side runs backward,
   flip the sign for that side in `cyberpi/mbot2_bridge.py` (`DRIVE` handler:
   `drive_power(l, -r)` — adjust per your chassis).
4. `stop` → wheels halt promptly (`EM_stop(port="all")` fallback `drive_power(0,0)`).
5. `forward(speed=50)` vs timed `FORWARD 50 1` → check speed feel + stop after 1 s.
6. `ultrasonic` → hold hand 10/20/50 cm in front, compare readings.
7. `line_sensor` → place on line / off line, confirm bit pattern changes
   (also confirms the `quad_rgb_sensor` `index=1` assumption in the bridge).
8. `gyro` → rotate the bot, watch roll/pitch/yaw move.
9. `battery` → sanity-check percentage.
10. Bluetooth (optional, untethered only): pair per Makeblock's guide; the BT link
    shows up as another serial port (`/dev/rfcomm0`, `/dev/tty.CyberPi-xxxx`,
    `COM6`). Put it in `MBOT2_BOTS` — zero code changes.

## 5. Fleet rollout (one USB pass per bot)

Label each bot (A/B/C/D) → repeat `02-bridge-upload.md` §3 with that bot plugged
in → record `A=<port>` mapping in opencode config. Afterwards everything is
remote/config.
