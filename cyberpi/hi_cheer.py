# cyberpi/hi_cheer.py
# Says hi and plays cheering notes: cyan LED ring + "Hi!" on screen,
# the built-in "hello" voice preset, then a C5-E5-G5-C6 arpeggio,
# ending green with a heartbeat marker on USB serial.
# Uses only confirmed APIs (docs/05-cyberpi-mbot2-api-reference.md).
#
# IMPORTANT: entry point must stay registered via @event.start (see
# AGENTS.md / history/2026-09-06_mlink-fix-and-bridge-upload-brick.md).

import cyberpi
import event
import time

MARKER = "HI-CHEER-5A1D9"


@event.start
def on_start():
    cyberpi.led.on(0, 255, 255, id='all')
    cyberpi.display.clear()
    cyberpi.display.show_label("Hi!", 24, 0, 20, 0)
    print(MARKER + " boot")
    cyberpi.audio.set_vol(100)
    cyberpi.audio.play_until("hello")
    for freq in (523, 659, 784, 1047):
        cyberpi.audio.play_tone(freq, 0.25)
    cyberpi.led.on(0, 255, 0, id='all')
    cyberpi.display.clear()
    cyberpi.display.show_label("Cheers!", 16, 0, 20, 0)
    while True:
        print(MARKER + " heartbeat")
        time.sleep(2)
# cheer-pad-012345678
