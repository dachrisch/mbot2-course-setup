# cyberpi/welcome_greeter.py
# Standalone CyberPi greeter: plays a speak -> dance -> end-text sequence
# once at boot. No PC/serial/MCP involved. See
# docs/05-cyberpi-mbot2-api-reference.md for the API calls used here, and
# docs/superpowers/specs/2026-09-06-cyberpi-welcome-greeter-design.md for
# the design this implements.
#
# IMPORTANT: entry point must stay registered via @event.start (see
# history/2026-09-06_mlink-fix-and-bridge-upload-brick.md) — a bare
# `if __name__ == "__main__"` block bricked this board twice.

import cyberpi
import event
import mbot2


def _speak_greet():
    cyberpi.led.on(0, 255, 255, id='all')
    cyberpi.audio.set_vol(100)
    cyberpi.display.show_label("Hello!", 24, 0, 20, 0)
    cyberpi.audio.play_until("hello")


@event.start
def on_start():
    _speak_greet()
