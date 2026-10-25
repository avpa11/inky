#!/usr/bin/env bash
# Run inside a freshly uploaded release directory, as the ordinary Pi user.
set -euo pipefail
release=$(cd "$(dirname "$0")/.." && pwd)
base="$HOME/inky-home"
if [[ $(uname -s) != Linux || ! -e /proc/device-tree/model ]]; then
  echo 'This installer is for a Raspberry Pi running Raspberry Pi OS.' >&2; exit 1
fi
if [[ ! -e /dev/spidev0.0 && ! -e /dev/spidev0.1 ]]; then
  # With spi0-0cs neither spidev node is expected; check the applied overlay config.
  if ! grep -q '^dtoverlay=spi0-0cs' /boot/firmware/config.txt; then
    echo 'Run Pimoroni inky/install.sh first, enable SPI/I2C, and reboot as requested.' >&2; exit 1
  fi
fi
free_kb=$(df -Pk "$HOME" | awk 'NR==2 {print $4}')
if (( free_kb < 300000 )); then echo 'At least 300 MB free disk is required.' >&2; exit 1; fi
python3 -m venv --system-site-packages "$release/.venv"
"$release/.venv/bin/python" -m pip install --no-cache-dir "$release[pi]"
"$release/.venv/bin/python" -c 'import inky, gpiod, gpiodevice, waitress; from inky_home.lessons import CATALOG; print("French daily sets:", CATALOG.validate())'
mkdir -p "$base/data" "$HOME/.config/systemd/user"
# Install a systemd USER service; preserve the previous release for rollback.
python3 - "$release" "$base" <<'PY'
import os, pathlib, sys, sqlite3
from datetime import datetime, timezone
release, base = map(pathlib.Path, sys.argv[1:])
state = base / 'data/home.sqlite3'
if state.is_file():
    backups = base / 'data/backups'
    backups.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    destination = backups / f'home-before-{stamp}.sqlite3'
    with sqlite3.connect(state.as_uri() + '?mode=ro', uri=True) as source, sqlite3.connect(destination) as backup:
        source.backup(backup)
    print(f'Saved state backup: {destination}')
current = base / 'current'
if current.is_symlink():
    previous = base / 'previous'
    previous.unlink(missing_ok=True)
    previous.symlink_to(current.resolve())
temporary = base / 'next'
temporary.unlink(missing_ok=True)
temporary.symlink_to(release)
os.replace(temporary, current)
unit = (release / 'deploy/inky-home.service').read_text().replace('@HOME@', str(pathlib.Path.home()))
(pathlib.Path.home() / '.config/systemd/user/inky-home.service').write_text(unit)
PY
# Lingering starts the user service at boot, even when nobody has logged in.
if [[ $(loginctl show-user "$USER" -p Linger --value) != yes ]]; then
  sudo loginctl enable-linger "$USER"
fi
systemctl --user daemon-reload
systemctl --user enable inky-home.service
systemctl --user restart inky-home.service
sleep 3
systemctl --user --no-pager status inky-home.service
printf '\nOpen http://small.local:8080 (or this Pi IP on port 8080).\n'
