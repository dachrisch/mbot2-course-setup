# CyberPi / mBot2 MicroPython API reference

Confirmed by inspecting [PerfecXX/mBot2](https://github.com/PerfecXX/mBot2)
(2026-09-06) — a community-maintained collection of MicroPython/Arduino
example code for mBot2/CyberPi, independent of mBlock. Its README confirms
what `AGENTS.md` already states as a hard constraint here: MicroPython
upload never touches CyberPi's firmware; Arduino (PlatformIO) does and
wipes CyberOS.

Use this instead of guessing API signatures — this repo's original
`mbot2_bridge.py` guessed `mbot2.drive_power(l, r)` / `mbot2.EM_stop(...)`
from older docs; neither appears in this confirmed example set (see
Movement below for the real method names).

## Import convention (confirmed)

```python
import cyberpi
import mbot2
import mbuild
import event
```

## Entry point (hard requirement — see `AGENTS.md`)

```python
import event

@event.start
def on_start():
    ...
```

## LED (`cyberpi.led`)

- `cyberpi.led.on(r, g, b, id=1..5|'all')` — set one or all of the 5 ring LEDs
- `cyberpi.led.off(id='all')`
- `cyberpi.led.play(name="rainbow")` — built-in animations:
  `rainbow`, `spoondrift`, `meteor_blue`, `meteor_green`, `flash_red`,
  `flash_orange`, `firefly`
- `cyberpi.led.move(n)` — shift the ring's colors n steps (negative = other
  direction)

## Audio (`cyberpi.audio`)

- `cyberpi.audio.set_vol(0-100)`
- `cyberpi.audio.play_until(name)` — blocking playback of a built-in preset
  clip. Full preset list:
  `hello, hi, bye, yeah, wow, laugh, hum, sad, sigh, annoyed, angry,
  surprised, yummy, curious, embarrassed, ready, sprint, sleepy, meow,
  start, switch, beeps, buzzing, explosion, jump, laser, level-up,
  low-energy, prompt-tone, right, wrong, ring, score, wake, warning,
  metal-clash, shot, glass-clink, inflator, running water, clockwork,
  click, current, switch, wood-hit, iron, drop, bubble, wave, magic,
  spitfire, heartbeat, load`
- `cyberpi.audio.play_drum(name, beat_seconds)` — drum hits: `snare,
  bass-drum, side-stick, crash-cymbal, open-hi-hat, close-hi-hat,
  tambourine, hand-clap, claves`
- `cyberpi.audio.play_tone(freq_hz, duration_seconds)`
- `cyberpi.audio.play_music(note=0-132, beat=seconds)` — MIDI-style note
- `cyberpi.cloud.tts(lang, text)` — **real text-to-speech**, but requires
  WiFi (`cyberpi.wifi.connect(ssid, pwd)`) plus a Makeblock cloud
  account/access token (`cyberpi.driver.cloud_translate.set_token(...)`,
  `TTS_URL`, etc.). Heavier dependency with more failure modes (WiFi
  availability, cloud credentials) — the offline preset clips above are
  simpler and more reliable for something like a startup greeting.

## Display (`cyberpi.display`)

- `cyberpi.display.show_label(text, size, x, y, index)` — `size` one of
  12/16/24/32; `index` 0-7 selects a display "slot" (multiple labels can
  coexist on screen at once, each in its own slot)
- `cyberpi.display.clear()`

## Movement (`mbot2`)

- `mbot2.forward(speed_rpm, seconds)` / `mbot2.backward(speed_rpm, seconds)`
- `mbot2.turn_left(speed_rpm, seconds)` / `mbot2.turn_right(speed_rpm, seconds)`
- `mbot2.straight(cm)` — move a specific distance (+forward / -backward)
- `mbot2.turn(degrees)` — rotate in place by a specific angle (+right / -left)

## Sensors (`mbuild`)

- `mbuild.ultrasonic2.get(index)` — confirmed working (used in this repo)
- `mbuild.quad_rgb_sensor.get_line_sta(index)` — line sensor states
  (this repo's assumption; not directly confirmed in the example set)

## Multi-bot communication (`cyberpi.wifi_broadcast`)

Relevant for a future "bots interact with each other" phase. Bots on the
same WiFi network can publish/read short string messages by topic, no
Bluetooth or MCP server involved:

```python
cyberpi.wifi_broadcast.set(topic, "message")   # broadcast
message = cyberpi.wifi_broadcast.get(topic)    # read latest
```

Requires WiFi (`cyberpi.wifi.connect(ssid, pwd)`,
`cyberpi.wifi.is_connect()`). This is the simplest confirmed path to
multi-bot interaction found so far.
