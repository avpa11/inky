#!/usr/bin/env bash
set -euo pipefail
target=${1:-user@small.local}
options=(-o ConnectTimeout=10)
if [[ -n ${INKY_KNOWN_HOSTS:-} ]]; then options+=(-o "UserKnownHostsFile=$INKY_KNOWN_HOSTS" -o StrictHostKeyChecking=yes); fi
ssh "${options[@]}" "$target" 'bash -s' <<'REMOTE'
set -eu
printf '\nBoard / OS\n'
tr -d '\000' < /proc/device-tree/model; echo
cat /etc/os-release
uname -m
printf '\nLoad / memory / disk\n'
uptime
free -h
df -h /
ps -eo pid,comm,pcpu,pmem --sort=-pcpu | head -n 12
printf '\nInky environment\n'
if [ -x "$HOME/.virtualenvs/pimoroni/bin/python" ]; then
  "$HOME/.virtualenvs/pimoroni/bin/python" -c 'import sys, inky; print(sys.executable); print(inky.__file__)'
else
  echo 'Pimoroni virtual environment not found. Complete the official Inky installer first.'
fi
printf '\nInterfaces / GPIO permissions\n'
ls -l /dev/spidev* /dev/i2c-* /dev/gpiochip* 2>/dev/null || true
id
printf '\nRelevant boot configuration\n'
grep -E 'dtparam=(spi|i2c)|dtoverlay=spi0' /boot/firmware/config.txt 2>/dev/null || true
REMOTE
