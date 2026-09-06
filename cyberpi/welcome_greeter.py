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


def _dance():
    moves = [
        (lambda: mbot2.turn(90), (0, 255, 0), "snare"),
        (lambda: mbot2.turn(-90), (255, 0, 255), "tambourine"),
        (lambda: mbot2.forward(40, 0.4), (0, 255, 255), "side-stick"),
        (lambda: mbot2.backward(40, 0.4), (255, 255, 0), "hand-clap"),
    ]
    for _ in range(2):
        for move, color, drum in moves:
            cyberpi.led.on(color[0], color[1], color[2], id='all')
            cyberpi.audio.play_drum(drum, 0.3)
            move()
    cyberpi.led.play(name="rainbow")


def _end_text():
    cyberpi.led.off(id='all')
    cyberpi.display.clear()
    cyberpi.display.show_label("Welcome to class!", 16, 0, 20, 0)


@event.start
def on_start():
    _speak_greet()
    _dance()
    _end_text()
