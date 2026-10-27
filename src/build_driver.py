"""Build a separately licensed BlackHole HAL plug-in without a full Xcode installation."""
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
from build_paths import ROOT,BUILD,LOGS,VERSION

BUNDLE_ID = 'local.hd300lab.USBBridge'
NAME = 'HD300USBBridge'
bundle = BUILD / (NAME + '.driver')
contents = bundle / 'Contents'
macos = contents / 'MacOS'
resources = contents / 'Resources'
macos.mkdir(parents=True, exist_ok=True)
resources.mkdir(parents=True, exist_ok=True)
source = ROOT / 'vendor/BlackHole/BlackHole/BlackHole.c'
cmd = ['xcrun', 'clang', '-arch', 'arm64', '-mmacosx-version-min=12.0',
       '-std=gnu11', '-O2', '-fblocks', '-bundle', '-framework', 'CoreAudio',
       '-framework', 'CoreFoundation', '-framework', 'Accelerate',
       '-DkDriver_Name="HD300USBBridge"',
       '-DkDevice_Name="POD HD300 USB Bridge %ich"',
       '-DkManufacturer_Name="HD300 Lab (BlackHole-based)"',
       '-DkPlugIn_BundleID="' + BUNDLE_ID + '"', '-DkNumber_Of_Channels=2',
       '-DkSampleRates=44100,48000', '-DkLatency_Frame_Size=0',
       str(source), '-o', str(macos / NAME)]
subprocess.run(cmd, check=True)
factory = 'c71e05a4-48fa-4df8-b2e7-31fdc475f030'
plist = {'CFBundleDevelopmentRegion': 'English', 'CFBundleExecutable': NAME,
         'CFBundleIdentifier': BUNDLE_ID, 'CFBundleInfoDictionaryVersion': '6.0',
         'CFBundleName': NAME, 'CFBundlePackageType': 'BNDL',
         'CFBundleShortVersionString': VERSION, 'CFBundleVersion': '1',
         'CFPlugInFactories': {factory: 'BlackHole_Create'},
         'CFPlugInTypes': {'443ABAB8-E7B3-491A-B985-BEB9187030DB': [factory]}}
(contents / 'Info.plist').write_bytes(plistlib.dumps(plist))
shutil.copy2(ROOT / 'vendor/BlackHole/BlackHole/BlackHole.icns', resources)
shutil.copy2(ROOT / 'vendor/BlackHole/LICENSE', resources / 'BlackHole-GPL-3.0.txt')
subprocess.run(['codesign', '--force', '--sign', '-', str(bundle)], check=True)
subprocess.run(['codesign', '--verify', '--deep', '--strict', str(bundle)], check=True)
revision = (ROOT/'vendor/blackhole-revision.txt').read_text().strip()
manifest = {'bundle_id': BUNDLE_ID, 'bundle': str(bundle),
            'system_path': '/Library/Audio/Plug-Ins/HAL/' + NAME + '.driver',
            'upstream_commit': revision, 'upstream_license': 'GPL-3.0',
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'binary_sha256': hashlib.sha256((macos / NAME).read_bytes()).hexdigest(),
            'compile_command': cmd, 'kernel_extension': False, 'startup_item': False}
(LOGS / 'driver-build.json').write_text(json.dumps(manifest, indent=2))
print(bundle)
