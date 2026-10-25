#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
target=${1:-user@small.local}
if [[ ! $target =~ ^[a-zA-Z0-9_.@:-]+$ ]]; then echo 'Invalid SSH target' >&2; exit 1; fi
options=(-o ConnectTimeout=10)
if [[ -n ${INKY_KNOWN_HOSTS:-} ]]; then
  if [[ $INKY_KNOWN_HOSTS == *[[:space:]]* ]]; then echo 'Known-hosts path must not contain spaces' >&2; exit 1; fi
  options+=(-o "UserKnownHostsFile=$INKY_KNOWN_HOSTS" -o StrictHostKeyChecking=yes)
fi
./scripts/inspect-pi.sh "$target"
release="release-$(date -u +%Y%m%dT%H%M%SZ)"
ssh "${options[@]}" "$target" "mkdir -p inky-home/releases/$release"
rsync -az --exclude .git --exclude .venv --exclude build --exclude dist --exclude var --exclude 'var-*' --exclude __pycache__ --exclude '*.egg-info' --exclude '.DS_Store' -e "ssh ${options[*]}" ./ "$target:inky-home/releases/$release/"
ssh -t "${options[@]}" "$target" "bash inky-home/releases/$release/scripts/install-on-pi.sh"
