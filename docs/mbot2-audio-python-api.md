# mBot2 / CyberPi Python API — Audio & Sound

## Scope

Sound generation and speaker control for the mBot2/CyberPi Python environment.

Makeblock's current documentation identifies `cyberpi` as the Python library for CyberPi products and directs users to the Python API documentation from the mBlock Python Editor. citeturn0search4

## Import

```python
import cyberpi
```

## `cyberpi.audio.play_tone()`

Play a tone at a specified frequency.

```python
cyberpi.audio.play_tone(frequency, duration)
```

Examples:

```python
cyberpi.audio.play_tone(440, 500)   # A4, 500 ms
cyberpi.audio.play_tone(262, 500)   # C4, 500 ms
cyberpi.audio.play_tone(1000, 100)  # 1 kHz, 100 ms
```

The CyberPi API documentation examples use `cyberpi.audio.play_tone()`. citeturn0search12

## `cyberpi.audio.play_note()`

Play a musical note for a number of beats.

```python
cyberpi.audio.play_note(note, beats)
```

Examples:

```python
cyberpi.audio.play_note("C4", 1)
cyberpi.audio.play_note("E4", 1)
cyberpi.audio.play_note("G4", 1)
cyberpi.audio.play_note("C5", 2)
```

A simple melody:

```python
import cyberpi

cyberpi.audio.play_note("C4", 1)
cyberpi.audio.play_note("E4", 1)
cyberpi.audio.play_note("G4", 1)
cyberpi.audio.play_note("C5", 2)
```

The underlying Makeblock MicroPython speaker API documents note names such as `C4` and numeric note values, with beats controlling note duration. citeturn0search0turn0search3

## `cyberpi.audio.set_vol()`

Set speaker volume.

```python
cyberpi.audio.set_vol(volume)
```

Typical range:

```text
0–100
```

Example:

```python
cyberpi.audio.set_vol(50)
```

Makeblock's speaker documentation specifies volume as 0–100. citeturn0search1

## `cyberpi.audio.stop()`

Stop the current audio playback.

```python
cyberpi.audio.stop()
```

> **Verification note:** The exact stop-method name has varied across Makeblock's different Python APIs and generations. Older Makeblock MicroPython documentation uses `stop_sound()` for the speaker module. Verify the exact method exposed by the CyberPi firmware installed on the mBot2 before using it in production. citeturn0search0

## Notes and frequencies

Common note/frequency mappings documented by Makeblock:

| Note | Frequency |
|---|---:|
| C2 | 65 Hz |
| D2 | 73 Hz |
| E2 | 82 Hz |
| F2 | 87 Hz |
| G2 | 98 Hz |
| A2 | 110 Hz |
| B2 | 123 Hz |
| C3 | 131 Hz |
| D3 | 147 Hz |
| E3 | 165 Hz |
| F3 | 175 Hz |
| G3 | 196 Hz |
| A3 | 220 Hz |
| B3 | 247 Hz |
| C4 | 262 Hz |
| D4 | 294 Hz |
| E4 | 330 Hz |
| F4 | 349 Hz |
| G4 | 392 Hz |
| A4 | 440 Hz |
| B4 | 494 Hz |
| C5 | 523 Hz |
| D5 | 587 Hz |
| E5 | 659 Hz |
| F5 | 698 Hz |
| G5 | 784 Hz |
| A5 | 880 Hz |
| B5 | 988 Hz |
| C6 | 1047 Hz |
| D6 | 1175 Hz |
| E6 | 1319 Hz |
| F6 | 1397 Hz |
| G6 | 1568 Hz |
| A6 | 1760 Hz |
| B6 | 1976 Hz |
| C7 | 2093 Hz |
| D7 | 2349 Hz |
| E7 | 2637 Hz |
| F7 | 2794 Hz |
| G7 | 3136 Hz |
| A7 | 3520 Hz |
| B7 | 3951 Hz |
| C8 | 4186 Hz |
| D8 | 4699 Hz |

These mappings are documented by Makeblock's speaker/buzzer API documentation. citeturn0search0turn0search2

## Tempo / beats

In Makeblock's underlying speaker API, `tempo` controls the duration of a beat:

```python
speaker.tempo = 60
```

The documented range is 6–600 BPM; at 60 BPM, one beat is one second. `play_note()` and `rest()` use this tempo. citeturn0search0

The exact CyberPi wrapper for tempo should be verified against the installed CyberPi API.

## Rest / pause

The underlying Makeblock speaker API provides:

```python
speaker.rest(beats)
```

Example:

```python
speaker.play_note("C4", 1)
speaker.rest(1)
speaker.play_note("G4", 1)
```

`rest()` pauses for a number of beats according to the configured tempo. citeturn0search0

## Playing audio files

Makeblock's speaker APIs also support playing stored audio files. The exact API differs between Makeblock product generations.

One current mBuild speaker API documents:

```python
speaker.play_music("filename")
speaker.play_music_until_done("filename")
speaker.mute()
speaker.set_vol(50)
speaker.add_vol(10)
speaker.get_vol()
speaker.is_play()
```

That API is for an mBuild speaker module, not necessarily the onboard CyberPi speaker, so do not assume these methods exist on the mBot2's onboard speaker. citeturn0search1

Older Makeblock MicroPython speaker APIs use:

```python
speaker.play_melody("filename")
speaker.play_melody_until_done("filename")
speaker.stop_sound()
```

and document WAV files stored on the device. citeturn0search0turn0search3

## Recommended minimal interface for an MCP bridge

For Codex → MCP → mBot2, expose a small stable interface rather than the entire low-level API:

```text
play_tone(frequency, duration_ms)
play_note(note, beats)
set_volume(volume)
stop_sound()
```

Optional higher-level commands:

```text
beep()
success_sound()
error_sound()
notification_sound()
play_melody(notes)
```

Example:

```python
def success_sound():
    cyberpi.audio.play_note("C5", 0.25)
    cyberpi.audio.play_note("E5", 0.25)
    cyberpi.audio.play_note("G5", 0.5)
```

## Important distinction

The sound API belongs to CyberPi:

```text
mBot2
└── CyberPi
    └── cyberpi.audio
        ├── play_tone(...)
        ├── play_note(...)
        ├── set_vol(...)
        └── stop / stop_sound (...)
```

It is separate from the mBot2 chassis API:

```python
mbot2.forward(...)
mbot2.backward(...)
mbot2.turn_left(...)
mbot2.turn_right(...)
mbot2.drive_power(...)
mbot2.drive_speed(...)
```

## Official/current documentation entry points

- Makeblock Programming Software: https://support.makeblock.com/hc/en-us/articles/7048529365271-Programming-Software
- mBlock Python Editor: https://python.mblock.cc/
- Makeblock CyberPi Help Center: https://support.makeblock.com/hc/en-us/sections/6973045213719-CyberPi
- Makeblock mBuild API documentation: https://support.makeblock.com/hc/en-us/articles/20072185354903-APIs-for-mBuild-Modules

## Sources

- Makeblock — Programming Software / CyberPi Python API entry point. citeturn0search4
- Makeblock — mBuild output modules / speaker API. citeturn0search1
- Makeblock MicroPython API — onboard speaker. citeturn0search0
- Makeblock MicroPython API — buzzer. citeturn0search2
- Makeblock official MicroPython API repository. citeturn0search3
