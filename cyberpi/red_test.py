# cyberpi/red_test.py
# Final end-to-end test of the browser-free uploader: brand-new program
# (not identical bytes). Turns the LED ring red, shows "RED test",
# prints a marker heartbeat. Small file (< 80 bytes of... no — full
# source; exercises the uploader with a different size/remainder).
#
# IMPORTANT: entry point must stay registered via @event.start (see
# AGENTS.md / history/2026-09-06_mlink-fix-and-bridge-upload-brick.md).

import cyberpi
import event
import time

MARKER = "RED-TEST-9F1C4"


@event.start
def on_start():
    cyberpi.led.on(255, 0, 0, id='all')
    cyberpi.display.clear()
    cyberpi.display.show_label("RED test", 16, 0, 20, 0)
    print(MARKER + " boot")
    while True:
        print(MARKER + " heartbeat")
        time.sleep(2)
# pad-to-800-for-uploader-test-00
##
