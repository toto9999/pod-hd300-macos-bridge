import argparse
import json
import math
from pathlib import Path
import wave

parser = argparse.ArgumentParser(description='Analyze PCM24 stereo recording without playback')
parser.add_argument('wav', type=Path)
args = parser.parse_args()
with wave.open(str(args.wav), 'rb') as wav:
    if wav.getnchannels() != 2 or wav.getsampwidth() != 3:
        raise SystemExit('Expected stereo PCM24 WAV')
    rate = wav.getframerate()
    frames = wav.getnframes()
    data = wav.readframes(frames)
channels = []
for ch in range(2):
    samples = [int.from_bytes(data[i:i+3], 'little', signed=True)
               for i in range(ch * 3, len(data), 6)]
    peak = max((abs(s) for s in samples), default=0)
    rms = math.sqrt(sum(s*s for s in samples) / len(samples)) if samples else 0
    db = lambda v: 20 * math.log10(v / 8388608) if v else None
    channels.append({'peak_dbfs': db(peak), 'rms_dbfs': db(rms),
                     'clipped_samples': sum(abs(s) >= 8388607 for s in samples)})
print(json.dumps({'wav': str(args.wav), 'frames': frames, 'sample_rate': rate,
                  'seconds': frames / rate, 'channels': channels}, indent=2))
