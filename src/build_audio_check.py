from pathlib import Path
import plistlib
import subprocess
from build_paths import ROOT as root,BUILD

app=BUILD/'HD300 Audio Check.app'
binary=app/'Contents/MacOS/HD300AudioCheck'
binary.parent.mkdir(parents=True,exist_ok=True)
subprocess.run(['xcrun','clang','-mmacosx-version-min=12.0','-fobjc-arc',str(root/'src/audio_check.m'),
                '-framework','Cocoa','-framework','AVFoundation','-framework','CoreAudio',
                '-o',str(binary)],check=True)
info={'CFBundleExecutable':'HD300AudioCheck','CFBundleIdentifier':'local.hd300lab.AudioCheck',
      'CFBundleName':'HD300 Audio Check','CFBundlePackageType':'APPL','CFBundleVersion':'1',
      'LSMinimumSystemVersion':'12.0',
      'NSMicrophoneUsageDescription':'HD300 가상 오디오 장치의 입력을 3초 동안 검사합니다. 가상 장치만 열고 마이크나 스피커 장치는 선택하지 않습니다.'}
(app/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
subprocess.run(['codesign','--force','--sign','-',str(app)],check=True)
print(app)
