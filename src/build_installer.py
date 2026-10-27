import json
from pathlib import Path
import shutil
import subprocess
from build_paths import ROOT,BUILD as build,LOGS,VERSION

target = '/Library/Audio/Plug-Ins/HAL/HD300USBBridge.driver'
staged = build / 'package-root' / target.lstrip('/')
if staged.exists():
    shutil.rmtree(staged)
staged.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(build / 'HD300USBBridge.driver', staged)
scripts = build / 'package-scripts'
scripts.mkdir(exist_ok=True)
(scripts / 'preinstall').write_text('''#!/bin/sh
set -eu
target=/Library/Audio/Plug-Ins/HAL/HD300USBBridge.driver
if [ -e "$target" ]; then
  id=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$target/Contents/Info.plist")
  [ "$id" = local.hd300lab.USBBridge ] || { echo 'Refusing to overwrite a different driver'; exit 1; }
fi
''')
(scripts / 'postinstall').write_text('''#!/bin/sh
set -eu
/usr/sbin/chown -R root:wheel /Library/Audio/Plug-Ins/HAL/HD300USBBridge.driver
/bin/chmod -R go-w /Library/Audio/Plug-Ins/HAL/HD300USBBridge.driver
# CoreAudio restarts automatically; currently playing audio is briefly interrupted.
/usr/bin/killall -TERM coreaudiod || true
''')
for p in scripts.iterdir():
    p.chmod(0o755)
pkg = build / f'HD300USBBridge-{VERSION}.pkg'
subprocess.run(['pkgbuild', '--root', str(build / 'package-root'), '--scripts', str(scripts),
                '--identifier', 'local.hd300lab.USBBridge', '--version', VERSION,
                '--ownership', 'recommended', '--install-location', '/', str(pkg)], check=True)
manifest = {'driver_path': target, 'package_receipt': 'local.hd300lab.USBBridge',
            'installer': str(pkg), 'startup_items': [], 'kernel_extensions': [],
            'source_folder': str(ROOT), 'uninstall': str(ROOT / 'Uninstall Bridge.command')}
manifest['user_approved_microphone_permission'] = 'local.hd300lab.AudioCheck'
(LOGS / 'system-install-manifest.json').write_text(json.dumps(manifest, indent=2))
print(pkg)
