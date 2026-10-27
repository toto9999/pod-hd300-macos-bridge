"""Start one visible, stoppable bridge service; no login item or launch agent."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[1]
pidfile = root / 'logs/bridge.pid'
if pidfile.exists():
    try:
        pid = int(pidfile.read_text())
        cmd = subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True)
        if str(root / 'src/bridge.py') in cmd.stdout:
            print('Bridge is already running. PID:',pid)
            raise SystemExit(0)
    except ValueError:
        pass
    pidfile.unlink()
with (root / 'logs/bridge-console.log').open('a') as log:
    process = subprocess.Popen([sys.executable,str(root/'src/bridge.py')],
                               cwd=root,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
for _ in range(50):
    if process.poll() is not None:
        raise SystemExit('Bridge did not start. See logs/bridge-console.log.')
    if pidfile.exists() and (root/'logs/bridge-status.json').exists():
        status_path=root/'logs/bridge-status.json'
        if status_path.stat().st_mtime > time.time()-3:
            status=json.loads(status_path.read_text())
            if status.get('pid') != process.pid:
                time.sleep(0.1)
                continue
            if status.get('state') != 'running' or not status.get('usb_bytes'):
                time.sleep(0.1)
                continue
            print('HD300 bridge is running. PID:',process.pid)
            print('GarageBand input:',status['output_device'])
            print('CoreAudio sample rate:',status['output_sample_rate'])
            print('Stop with Stop Bridge.command or ./run.sh stop.')
            break
    time.sleep(0.1)
else:
    print('Bridge process launched. Check logs/bridge-console.log and logs/bridge-status.json.')
