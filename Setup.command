#!/bin/sh
set -eu
cd "$(dirname "$0")"
root=$PWD
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ] || {
  echo 'This experimental build supports Apple Silicon macOS only.'; exit 1;
}
mkdir -p .cache/downloads .tools .python logs recordings build
if [ -f logs/bridge.pid ] && kill -0 "$(cat logs/bridge.pid)" 2>/dev/null; then
  echo 'Stop the running bridge before setup or dependency installation.'; exit 1;
fi
export UV_CACHE_DIR="$root/.cache/uv"
export UV_PYTHON_INSTALL_DIR="$root/.python"
export UV_PYTHON_BIN_DIR="$root/.tools"
export UV_NO_CONFIG=1
if [ ! -x .tools/uv ]; then
  base=https://github.com/astral-sh/uv/releases/download/0.13.6
  archive=uv-aarch64-apple-darwin.tar.gz
  curl -fL --retry 3 "$base/$archive" -o ".cache/downloads/$archive"
  curl -fL --retry 3 "$base/$archive.sha256" -o .cache/downloads/uv.sha256
  expected=$(awk '{print $1;exit}' .cache/downloads/uv.sha256)
  printf '%s  %s\n' "$expected" ".cache/downloads/$archive" | shasum -a 256 -c -
  tar -xzf ".cache/downloads/$archive" -C .tools --strip-components=1
fi
.tools/uv python install --no-bin 3.12.16
if [ ! -x .venv/bin/python ]; then
  .tools/uv venv --no-project --managed-python --python 3.12.16 .venv
fi
.tools/uv pip install --python .venv/bin/python -r requirements.txt
if [ ! -f settings.json ]; then cp settings.example.json settings.json; fi
version=$(cat VERSION)
if [ ! -f build/libhd300-resample.dylib ] || [ ! -d 'build/HD300 Control.app' ] || [ ! -f build/bridge-level ] || [ ! -f "build/HD300USBBridge-$version.pkg" ]; then
  echo 'Building native components. Command Line Tools are required for a source checkout.'
  .venv/bin/python src/build_all.py
fi
echo 'Setup complete. Run Install Bridge.command once, then HD300 Control.command.'
