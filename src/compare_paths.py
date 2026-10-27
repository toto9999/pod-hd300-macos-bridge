"""Compare simultaneous raw USB and authorized HAL recordings after independent resampling."""
import json
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import correlate, resample_poly

root=Path(__file__).resolve().parents[1]
def read(path):
    rate, data=wavfile.read(path)
    if np.issubdtype(data.dtype,np.integer):
        data=data.astype(np.float64)/(np.iinfo(data.dtype).max+1)
    return rate,np.asarray(data,dtype=np.float64)
rate,usb=read(root/'recordings/usb-diagnostic.wav')
out_rate,hal=read(root/'recordings/hal-diagnostic.wav')
from math import gcd
divisor=gcd(rate,out_rate)
reference=resample_poly(usb,out_rate//divisor,rate//divisor)
if len(hal)>len(reference):
    raise SystemExit('HAL recording is longer than USB recording; repeat synchronized capture')
report={'usb_rate':rate,'hal_rate':out_rate,'hal_seconds':len(hal)/out_rate,'channels':[]}
for ch in range(2):
    x=reference[:,ch];y=hal[:,ch]
    n=len(y)
    energy=np.r_[0,np.cumsum(x*x)]
    denom=np.sqrt(np.maximum(energy[n:]-energy[:-n],1e-30)*max(float(y@y),1e-30))
    corr=correlate(x,y,mode='valid',method='fft')/denom
    lag=int(np.argmax(corr));matched=x[lag:lag+n]
    gain=float(matched@y)/max(float(matched@matched),1e-30)
    residual=y-gain*matched
    blocks=[]
    for at in range(0,n-out_rate//10,out_rate//10):
        segment=y[at:at+out_rate//10]
        lo=max(0,lag+at-96);hi=min(len(x),lag+at+len(segment)+96)
        local=correlate(x[lo:hi],segment,mode='valid',method='fft')
        blocks.append(int(lo+np.argmax(local)-at))
    report['channels'].append({'normalized_correlation':float(corr[lag]),'reference_offset_frames':lag,
        'gain':gain,'hal_peak':float(np.max(abs(y))),'hal_rms':float(np.sqrt(np.mean(y*y))),
        'relative_residual_rms':float(np.sqrt(np.mean(residual**2))/max(np.sqrt(np.mean(y*y)),1e-15)),
        'local_lag_span_frames':max(blocks)-min(blocks) if blocks else None})
(root/'logs/path-comparison.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
