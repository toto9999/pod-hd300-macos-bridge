import os
from pathlib import Path
import signal
import subprocess
import time

root = Path(__file__).resolve().parents[1]
pidfile = root / 'logs/bridge.pid'
if not pidfile.exists():
    print('Bridge is not running.')
    raise SystemExit(0)
pid = int(pidfile.read_text())
cmd = subprocess.run(['ps', '-p', str(pid), '-o', 'command='], capture_output=True, text=True)
matches = str(root / 'src/bridge.py') in cmd.stdout
if not matches and 'src/bridge.py' in cmd.stdout:
    cwd = subprocess.run(['lsof','-a','-p',str(pid),'-d','cwd','-Fn'],capture_output=True,text=True)
    matches = ('n'+str(root)) in cwd.stdout.splitlines()
if not matches:
    print('PID no longer belongs to this bridge; no process was stopped.')
    pidfile.unlink()
    raise SystemExit(0)
os.kill(pid, signal.SIGTERM)
for _ in range(100):
    if not pidfile.exists():
        print('Bridge stopped; USB interface released.')
        break
    time.sleep(0.1)
else:
    raise SystemExit('Bridge did not stop in 10 seconds; unplug HD300 and close its terminal.')
