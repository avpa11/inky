#!/usr/bin/env bash
# Run on the Pi. Application data is shared and remains intact.
set -euo pipefail
python3 - <<'PY'
import os
from pathlib import Path
base = Path.home() / 'inky-home'
previous = base / 'previous'
if not previous.is_symlink() or not previous.resolve().is_dir():
    raise SystemExit('No previous release is available')
current = base / 'current'
old, target = current.resolve(), previous.resolve()
next_link = base / 'next'
next_link.unlink(missing_ok=True)
next_link.symlink_to(target)
os.replace(next_link, current)
previous.unlink()
previous.symlink_to(old)
PY
systemctl --user restart inky-home
systemctl --user --no-pager status inky-home
