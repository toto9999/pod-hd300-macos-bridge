#!/bin/sh
set -eu
[ "$(id -u)" -eq 0 ] || { echo 'Run via Uninstall Bridge.command'; exit 1; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
target=/Library/Audio/Plug-Ins/HAL/HD300USBBridge.driver
if [ -e "$target" ]; then
  id=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$target/Contents/Info.plist")
  [ "$id" = local.hd300lab.USBBridge ] || { echo 'Refusing to move a different driver'; exit 1; }
  mkdir -p "$root/uninstalled"
  mv "$target" "$root/uninstalled/HD300USBBridge-$(date +%Y%m%d-%H%M%S).driver"
fi
/usr/sbin/pkgutil --forget local.hd300lab.USBBridge || true
/usr/bin/killall -TERM coreaudiod || true
echo 'Uninstalled. The driver copy is preserved inside this experiment folder.'
