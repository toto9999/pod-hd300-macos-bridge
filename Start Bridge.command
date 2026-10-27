#!/bin/sh
set -eu
cd "$(dirname "$0")"
exec .venv/bin/python "$PWD/src/start_bridge.py"
