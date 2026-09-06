# Linux setup — mLink driver + serial permissions

Date verified: 2026-09-06 · Host: Ubuntu 26.04 amd64 · Bot port: `/dev/ttyUSB0` (CH340 `1a86:7523`)

There is **no native mBlock 5 PC client for Linux**. The supported path is:

```
mLink driver (background daemon) + mBlock web IDE in Chrome/Edge
    https://ide.mblock.cc/      (blocks)
    https://python.mblock.cc/   (Python — use this for the bridge upload)
```

(Newer Chrome/Edge can also use WebSerial direct connection without mLink,
but mLink is the documented, reliable route — use it.)

## 1. Download mLink

- URL: **<https://s.mblock.cc/download/mlink-deb>** (.deb, mLink 1.2.0 at time of writing).
- Gotcha (verified 2026-09-06): the URL serves a JS countdown page that then
  redirects to `https://dls.makeblock.com/mblock5/linux/mLink-1.2.0-amd64.deb`.
  `curl` on either URL returns a ~5 KB HTML page, **not** the .deb — download it
  **in the browser** (click the button, keep the `mLink-1.2.0-amd64.deb` file).
  Direct `curl`/`wget` of the `dls.`/`dl.` links also returned HTML; do not
  script this download, fetch it by hand.

## 2. Install

```bash
sudo dpkg -i ~/Downloads/mLink-1.2.0-amd64.deb
```

Installs to `/usr/local/makeblock/mLink/` (launcher script `mlink`, bundled
node binary `mnode`, app `app.js`). No binary lands on `$PATH` — that is normal.

## 3. Start the daemon

```bash
/usr/local/makeblock/mLink/mlink start
# Start mlink: Running... / Version: 1.2.0
```

Verify it listens on port **55278** (this is how the web IDE talks to it):

```bash
(ss -tln || netstat -tln) | grep 55278
# LISTEN ... *:55278
```

Stop with `/usr/local/makeblock/mLink/mlink stop`. Logs: redirect stdout
(`.../mlink start >/tmp/mlink.log 2>&1`) — the daemon logs version + socket events.

## 4. Serial port permissions (dialout)

The CyberPi enumerates as `/dev/ttyUSB0`, owned `root:dialout` mode `660`.
Without the group you get `PermissionError: [Errno 13] Permission denied`.

```bash
ls -l /dev/ttyUSB0
# crw-rw---- 1 root dialout 188, 0 ... /dev/ttyUSB0

sudo usermod -aG dialout $USER
# then LOG OUT + BACK IN (group membership needs a fresh login).
# Immediate workaround without relogin:
sg dialout -c "python3 scripts/list_ports.py"
```

Find your port (plug in, compare before/after):

```bash
python3 scripts/list_ports.py
# /dev/ttyUSB0  USB Serial [1a86:7523]   <- the CyberPi (CH340)
# /dev/ttyS* entries are internal UARTs — ignore them.
```

## 5. Next

→ `02-bridge-upload.md` (connect in Chrome, upload the bridge, verify PING).
