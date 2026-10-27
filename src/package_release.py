"""Produce a source-complete runtime kit without local state or Python environments."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
from build_paths import ROOT,BUILD,VERSION

def git_files(where):
    return subprocess.check_output(['git','-C',str(where),'ls-files','-z']).decode().split('\0')[:-1]

subprocess.run(['git','-C',str(ROOT),'diff','--exit-code','--quiet'],check=True)
subprocess.run(['git','-C',str(ROOT),'diff','--cached','--exit-code','--quiet'],check=True)
revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
pinned=(ROOT/'vendor/blackhole-revision.txt').read_text().strip()
actual=subprocess.check_output(['git','-C',str(ROOT/'vendor/BlackHole'),'rev-parse','HEAD'],text=True).strip()
if actual!=pinned:
    raise SystemExit('BlackHole submodule differs from the pinned source revision')
out=ROOT/'build/releases'
out.mkdir(parents=True,exist_ok=True)
stem=f'pod-hd300-macos-bridge-{VERSION}-arm64'
archive=out/(stem+'.zip')
files={}
for relative in git_files(ROOT):
    source=ROOT/relative
    if source.is_file():
        files[relative]=source
for relative in git_files(ROOT/'vendor/BlackHole'):
    source=ROOT/'vendor/BlackHole'/relative
    if source.is_file():
        files['vendor/BlackHole/'+relative]=source
artifacts=['libhd300-resample.dylib','bridge-level','audio-state',
           'HD300 Control.app','HD300 Audio Check.app','HD300USBBridge.driver',
           f'HD300USBBridge-{VERSION}.pkg']
for artifact in artifacts:
    source=BUILD/artifact
    if not source.exists():
        raise SystemExit('Missing build artifact: '+str(source))
    if source.is_dir():
        for p in source.rglob('*'):
            if p.is_file():
                files['build/'+str(p.relative_to(BUILD))]=p
    else:
        files['build/'+artifact]=source
for name in files:
    if any(part in {'.git','.venv','.cache','.python','.tools','logs','recordings','uninstalled','__pycache__'} for part in Path(name).parts):
        raise SystemExit('Refusing to package local data: '+name)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for relative,source in sorted(files.items()):
        z.write(source,stem+'/'+relative)
    z.writestr(stem+'/SOURCE_VERSION.json',json.dumps({'version':VERSION,'commit':revision,
        'blackhole_commit':pinned,'architecture':'arm64','channel':'experimental',
        'notarized':False,'developer_id_signed':False},indent=2))
installer=out/f'HD300USBBridge-{VERSION}-arm64.pkg'
shutil.copy2(BUILD/f'HD300USBBridge-{VERSION}.pkg',installer)
sums=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in [archive,installer])
(out/'SHA256SUMS.txt').write_text(sums)
print(json.dumps({'archive':str(archive),'installer':str(installer),'files':len(files)},indent=2))
