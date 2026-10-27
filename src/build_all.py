import subprocess
import sys
from build_paths import ROOT,BUILD

if not (ROOT/'vendor/BlackHole/BlackHole/BlackHole.c').exists():
    raise SystemExit('BlackHole source missing. Clone with --recurse-submodules or run git submodule update --init.')
commands=[
    ['xcrun','clang','-O3','-arch','arm64','-mmacosx-version-min=12.0','-dynamiclib',str(ROOT/'src/resample.c'),'-o',str(BUILD/'libhd300-resample.dylib')],
    ['xcrun','clang','-O2','-mmacosx-version-min=12.0',str(ROOT/'src/bridge_level.c'),'-framework','CoreAudio','-framework','CoreFoundation','-o',str(BUILD/'bridge-level')],
    ['xcrun','clang','-mmacosx-version-min=12.0',str(ROOT/'src/audio_state.m'),'-framework','Foundation','-framework','AVFoundation','-framework','CoreAudio','-o',str(BUILD/'audio-state')],
]
for command in commands:
    subprocess.run(command,check=True)
for script in ['build_driver.py','build_control.py','build_audio_check.py','build_installer.py']:
    subprocess.run([sys.executable,str(ROOT/'src'/script)],check=True)
