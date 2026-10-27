#!/bin/sh
set -eu
cd "$(dirname "$0")"
case "${1:-help}" in
  probe) exec .venv/bin/python src/probe.py ;;
  record) shift; exec .venv/bin/python src/capture.py "$@" ;;
  analyze) shift; exec .venv/bin/python src/analyze.py "$@" ;;
  bridge) shift; exec .venv/bin/python "$PWD/src/bridge.py" "$@" ;;
  start) exec .venv/bin/python "$PWD/src/start_bridge.py" ;;
  stop) exec .venv/bin/python "$PWD/src/stop_bridge.py" ;;
  *) printf '%s\n' './run.sh start' './run.sh stop' './run.sh bridge --list-devices' './run.sh probe' './run.sh record --seconds 10' './run.sh analyze recordings/FILE.wav' ;;
esac
