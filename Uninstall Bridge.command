#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ -x .venv/bin/python ]; then
  .venv/bin/python "$PWD/src/stop_bridge.py"
elif [ -f logs/bridge.pid ] && kill -0 "$(cat logs/bridge.pid)" 2>/dev/null; then
  echo 'Stop the existing bridge before uninstalling; its Python environment is unavailable.'
  exit 1
fi
/usr/bin/tccutil reset Microphone local.hd300lab.AudioCheck || true
printf '%s\n' 'Administrator authentication is needed to remove the HAL plug-in.'
sudo /bin/sh "$PWD/src/uninstall_driver.sh"
