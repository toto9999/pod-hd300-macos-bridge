from pathlib import Path
import plistlib,subprocess
from build_paths import ROOT as root,BUILD
app=BUILD/'HD300 Control.app'
binary=app/'Contents/MacOS/HD300Control'
binary.parent.mkdir(parents=True,exist_ok=True)
subprocess.run(['xcrun','clang','-O2','-mmacosx-version-min=12.0','-fobjc-arc',str(root/'src/control.m'),'-framework','Cocoa','-o',str(binary)],check=True)
info={'CFBundleExecutable':'HD300Control','CFBundleIdentifier':'local.hd300lab.Control',
      'CFBundleName':'HD300 Control','CFBundlePackageType':'APPL','CFBundleVersion':'1',
      'NSHighResolutionCapable':True,'LSMinimumSystemVersion':'12.0'}
(app/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
subprocess.run(['codesign','--force','--sign','-',str(app)],check=True)
print(app)
