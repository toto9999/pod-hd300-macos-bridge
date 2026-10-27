#!/bin/sh
set -eu
cd "$(dirname "$0")"
version=$(cat VERSION)
open "$PWD/build/HD300USBBridge-$version.pkg"
