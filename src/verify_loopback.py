"""Verify only the virtual HAL path with low-level synthetic stereo tones."""
import json
from pathlib import Path
import numpy as np
import sounddevice as sd

ROOT = Path(__file__).resolve().parents[1]
name = 'POD HD300 USB Bridge 2ch'
indices = [i for i,d in enumerate(sd.query_devices()) if d['name'] == name]
if len(indices) != 1:
    raise SystemExit('Expected exactly one HD300 bridge device')
index = indices[0]
rate = int(sd.query_devices(index)['default_samplerate'])
count = 0
chunks = []
statuses = []
frequencies = [997, 1499]
def callback(indata, outdata, frames, timing, status):
    global count
    chunks.append(indata.copy())
    if status:
        statuses.append(str(status))
    t = (count + np.arange(frames)) / rate
    for ch, frequency in enumerate(frequencies):
        outdata[:, ch] = 0.001 * np.sin(2 * np.pi * frequency * t)
    count += frames
with sd.Stream(device=(index,index), channels=2, samplerate=rate,
               dtype='float32', blocksize=256, callback=callback):
    sd.sleep(2500)
recording = np.concatenate(chunks)[rate // 2: rate * 2]
results = []
for ch, expected in enumerate(frequencies):
    values = recording[:, ch]
    spectrum = abs(np.fft.rfft(values * np.hanning(len(values))))
    actual = float(np.argmax(spectrum) * rate / len(values))
    rms = float(np.sqrt(np.mean(values ** 2)))
    results.append({'expected_hz': expected, 'actual_hz': actual, 'rms': rms,
                    'passed': abs(expected-actual)<2 and 0.0005<rms<0.001})
report = {'device':name,'sample_rate':rate,'channels':results,'callback_status':statuses,
          'passed':all(r['passed'] for r in results) and not statuses}
(ROOT / 'logs/hal-loopback-test.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
