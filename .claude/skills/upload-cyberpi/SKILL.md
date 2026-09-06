---
name: upload-cyberpi
description: Upload a MicroPython file to the CyberPi via the mBlock web IDE using browser automation (claude-in-chrome or chrome-devtools-mcp). Use when the user asks to upload/flash/test code on the CyberPi/mBot2.
---

# Upload to CyberPi

Uploads a local MicroPython file to the CyberPi via `ide.mblock.cc`'s Upload
mode, using browser automation instead of manual copy-paste-click.
Codifies the procedure worked out the hard way on 2026-09-06 — two firmware
reinstalls happened before this was solid. Read
`history/2026-09-06_mlink-fix-and-bridge-upload-brick.md` if anything below
is unclear or something goes wrong; do not rediscover these lessons from
scratch.

## Usage

`/upload-cyberpi <path-to-.py-file>`

The file path is **required** — there is no default. If the user invokes
this without a path, ask which file, don't guess.

## Hard constraints (do not skip)

- **Never touch the mlink daemon** (`mlink start`/`stop`, restart, etc.)
  while doing this. Restarting it while a browser tab holds a connection is
  a leading suspect in the very first brick incident this session.
- **Never simulate keystrokes to enter code into the editor.** Set the
  Monaco editor's content directly via
  `monaco.editor.getModels()[0].setValue(code)` through the JS execution
  tool. Keystroke typing risks the editor's auto-indent/auto-bracket
  behavior corrupting the file.
- **Verify byte-for-byte before uploading.** Compare
  `new TextEncoder().encode(model.getValue()).length` against the local
  file's UTF-8 byte length (`wc -c`). Do not click Upload until they match
  exactly.
- **Warn (do not block) if `import event` / `@event.start` is missing from
  the file.** CyberPi's runtime requires the program entry point to be
  registered via `@event.start`; a bare `if __name__ == "__main__"` block
  or unregistered top-level code has bricked this board twice (boots to the
  Makeblock logo, then hangs/goes dark, requiring a firmware reinstall) —
  independent of what the code actually does. If missing, tell the user
  plainly and ask them to confirm before continuing.
- **Never assume success from the upload log or mBlock's own "Send" test
  box.** Both have produced misleading signals this session (a
  completed-looking log preceded a brick; the Send box showed nothing even
  when the upload was actually fine). The only trustworthy signal is the
  user physically confirming the board's behavior after upload.

## Steps

1. **Read the target file.** Get its exact content and UTF-8 byte length
   (`wc -c <path>`).
2. **Check for `@event.start`.** Grep the file for `@event.start` and
   `import event`. If either is missing, tell the user plainly what's
   missing and why it matters (see constraint above), and ask them to
   confirm they want to proceed anyway.
3. **Get/create a browser tab on `ide.mblock.cc`.**
   - Load the claude-in-chrome tools if not already loaded: `ToolSearch`
     with
     `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__tabs_create_mcp`.
   - Call `tabs_context_mcp`. If an existing tab in the group is already on
     `ide.mblock.cc`, ask the user whether it's the one they've already
     connected before reusing it. Otherwise create a new tab and navigate
     to `https://ide.mblock.cc/`.
   - If using `chrome-devtools-mcp` instead, the equivalent tools are
     `list_pages`/`new_page`/`navigate_page`, `evaluate_script`,
     `take_screenshot`, `click`.
4. **Confirm the device is connected, in Upload mode.** Take a screenshot.
   Look for the device panel showing a connected indicator (green dot /
   "Device connected") and the "Upload" toggle active (not "Live").
   - **If not connected: stop and ask the user to connect it themselves.**
     Both Bluetooth pairing and the WebSerial device picker are native
     OS/browser dialogs that cannot be clicked through by browser
     automation — this was hit twice this session (once with the tab
     becoming unresponsive to `tabs_close_mcp`, consistent with a stuck
     native dialog). Do not click "Bluetooth" or "Serial" and then wait for
     a dialog yourself; ask the user to do it and tell you when it's
     connected.
   - If connected but in "Live" mode, click "Upload" (a confirmation dialog
     may appear — click through it).
5. **Switch to the Python code tab** if the Blocks view is showing (click
   "Python" in the top-right of the editor pane).
6. **Set the editor content** via `javascript_tool`:
   ```js
   const code = `<exact file content, JS-escaped>`;
   const model = monaco.editor.getModels()[0];
   model.setValue(code);
   const v = model.getValue();
   JSON.stringify({charLength: v.length, byteLengthUtf8: new TextEncoder().encode(v).length, lines: model.getLineCount()});
   ```
   Compare `byteLengthUtf8` against the local file's byte count from step
   1. If they don't match, stop and investigate — do not upload.
7. **Screenshot to visually sanity-check** the code looks right (correct
   syntax highlighting, no obvious truncation) before uploading.
8. **Click "Upload Code."** Wait a few seconds, then screenshot. Watch for:
   - An "Upload Progress" dialog completing to 100% and closing itself, or
     a "The code has been uploaded" toast — both are normal-looking
     outcomes, but neither is proof the board is healthy (see constraint
     above).
   - Any visible error text, or a dialog that doesn't close on its own.
9. **Always ask the user a physical-check question afterward.** Something
   like: "Upload completed. Can you confirm the board looks healthy — did
   you see \[whatever this code's boot behavior should look like: an LED
   blip, a screen message, etc.\], and is it responsive (not stuck on the
   boot logo)?" Do not declare success until they confirm.
10. **If the user reports the board went dark/unresponsive:** stop
    immediately, don't retry, don't touch mlink/the device further, and
    help them document the incident (see
    `history/2026-09-06_mlink-fix-and-bridge-upload-brick.md` for the
    format this repo uses) rather than guessing at another fix.

## Known limitations

- This only works over whatever connection (USB/Serial via mLink, or
  Bluetooth) the user has already established in the browser tab — it does
  not establish that connection itself.
- Bluetooth on this specific CyberPi is BLE/GATT-only (not classic SPP) —
  see `history/2026-09-06_mlink-fix-and-bridge-upload-brick.md` Part 7.
  This skill can upload code over that connection (mBlock's browser already
  does), but this repo's own `SerialTransport` cannot talk to the board
  over Bluetooth after upload — only over USB.
