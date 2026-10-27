"""Bounded stereo FIFO with fractional resampling for independent USB/CoreAudio clocks."""
from threading import Lock
import ctypes
from pathlib import Path
import numpy as np

_library_path=Path(__file__).resolve().parents[1]/'build/libhd300-resample.dylib'
_native=None
if _library_path.exists():
    _library=ctypes.CDLL(str(_library_path))
    _native=_library.hd300_resample
    _array=np.ctypeslib.ndpointer(dtype=np.float32,flags='C_CONTIGUOUS')
    _native.argtypes=[_array,ctypes.c_int,ctypes.c_int64,ctypes.c_double,
                     ctypes.c_double,_array,_array,ctypes.c_int]
    _native.restype=None

def prioritize_usb_thread():
    if _native and hasattr(_library,'hd300_usb_thread_priority'):
        return _library.hd300_usb_thread_priority()
    return None

class AudioBuffer:
    def __init__(self, capacity=96000, target=512):
        self.data = np.zeros((capacity, 2), dtype=np.float32)
        self.capacity = capacity
        self.target = target
        self.read = self.write = 0
        self.phase = 0.0
        self.ready = False
        self.lock = Lock()
        self.underruns = self.overflows = 0
        self.max_queued = 0
        self.filtered_error = 0.0
        self.kernel_ratio = None
        self.kernel = None
        self.offsets = np.arange(-15, 17)
        self.peak = 0.0
        self.square_sum = 0.0
        self.sample_count = 0
        self.meter_peak = self.meter_square_sum = self.meter_count = 0
        self.output_meter_peak = 0.0
        self.output_overrange_samples = 0
        self.meter_overrange_samples = 0
        self.gain_db = 0.0
        self.current_gain = 1.0
        self.latency_resets = 0
        self.dropped_backlog_frames = 0
        self.last_output = np.zeros(2,dtype=np.float32)

    def configure(self,target=None,gain_db=None):
        with self.lock:
            if target is not None:
                self.target = target
                self.filtered_error = 0.0
            if gain_db is not None:
                self.gain_db = gain_db

    def push_pcm24(self, raw):
        if len(raw) % 6:
            raise ValueError('USB packet is not a complete PCM24 stereo frame')
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        values = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        values = (values ^ 0x800000) - 0x800000
        self.push((values.reshape(-1, 2) / 8388608.0).astype(np.float32))

    def push(self, values):
        count = len(values)
        if count > self.capacity:
            raise ValueError('Batch exceeds FIFO capacity')
        with self.lock:
            queued = self.write - self.read
            if queued + count > self.capacity:
                # Drop oldest frames only; bound memory and latency after a stalled consumer.
                self.read = self.write + count - self.capacity
                self.phase = 0.0
                self.overflows += 1
            at = (self.write + np.arange(count)) % self.capacity
            self.data[at] = values
            self.peak = max(self.peak, float(np.max(np.abs(values)))) if count else self.peak
            energy = float(np.sum(values.astype(np.float64) ** 2))
            self.square_sum += energy
            self.sample_count += values.size
            self.meter_peak = max(self.meter_peak,float(np.max(np.abs(values)))) if count else self.meter_peak
            self.meter_square_sum += energy
            self.meter_count += values.size
            self.write += count
            self.max_queued = max(self.max_queued, self.write - self.read)

    def prepare(self, nominal_ratio):
        if self.kernel_ratio == nominal_ratio:
            return
        fraction = np.arange(1024)[:, None] / 1024
        distance = self.offsets[None, :] - fraction
        cutoff = 0.94 / max(1.0, nominal_ratio)
        window = np.where(np.abs(distance) < 16,
                          0.42 + 0.5*np.cos(np.pi*distance/16)
                          + 0.08*np.cos(2*np.pi*distance/16), 0)
        kernel = cutoff * np.sinc(cutoff * distance) * window
        kernel /= kernel.sum(axis=1)[:, None]
        self.kernel = kernel.astype(np.float32)
        self.kernel_ratio = nominal_ratio

    def render(self, output, nominal_ratio=1.0):
        output.fill(0)
        with self.lock:
            count = len(output)
            queued = self.write - self.read
            catch_up = queued > max(self.target*3,self.target+480)
            if catch_up:
                # Resume at live audio after a stalled consumer instead of replaying a backlog.
                dropped=queued-self.target
                self.read+=dropped
                self.phase=0.0
                self.filtered_error=0.0
                queued=self.target
                self.latency_resets+=1
                self.dropped_backlog_frames+=dropped
            if not self.ready:
                if queued < max(self.target, int(count * nominal_ratio) + 17):
                    return
                self.ready = True
            if self.kernel_ratio != nominal_ratio:
                self.prepare(nominal_ratio)
            # Smooth scheduling jitter before correcting the independent USB clock.
            self.filtered_error += 0.01 * (queued - self.target - self.filtered_error)
            correction = np.clip(self.filtered_error * 0.000005, -0.001, 0.001)
            step = nominal_ratio * (1 + correction)
            positions = self.phase + np.arange(count) * step
            indices = positions.astype(np.int64)
            if indices[-1] + 16 >= queued:
                self.underruns += 1
                self.ready = False
                return
            if _native:
                _native(self.data,self.capacity,self.read,self.phase,step,self.kernel,output,count)
            else:
                phases = ((positions - indices) * 1024).astype(np.int64)
                samples = self.data[(self.read + indices[:, None] + self.offsets) % self.capacity]
                output[:] = np.einsum('nt,ntc->nc', self.kernel[phases], samples)
            desired = 10**(self.gain_db/20)
            next_gain = self.current_gain + 0.02*(desired-self.current_gain)
            if self.current_gain != 1 or next_gain != 1:
                output *= np.linspace(self.current_gain,next_gain,count,dtype=np.float32)[:,None]
            self.current_gain = next_gain
            if catch_up:
                fade=min(64,count)
                weight=np.linspace(0,1,fade,dtype=np.float32)[:,None]
                output[:fade]=self.last_output[None,:]*(1-weight)+output[:fade]*weight
            self.last_output[:]=output[-1]
            self.output_meter_peak = max(self.output_meter_peak,float(np.max(np.abs(output))))
            overrange = int(np.count_nonzero(np.abs(output)>1))
            self.output_overrange_samples += overrange
            self.meter_overrange_samples += overrange
            advanced = self.phase + count * step
            consumed = int(advanced)
            self.read += consumed
            self.phase = advanced - consumed

    def snapshot(self,reset_meter=False):
        with self.lock:
            result = {'queued_frames': self.write - self.read, 'underruns': self.underruns,
                    'overflows': self.overflows, 'max_queued_frames': self.max_queued,
                    'queue_delay_ms': (self.write-self.read)/48,
                    'resampler_backend':'native C' if _native else 'NumPy',
                    'input_peak_dbfs': float(20*np.log10(self.peak)) if self.peak else None,
                    'input_rms_dbfs': float(10*np.log10(self.square_sum/self.sample_count)) if self.square_sum else None,
                    'meter_peak_dbfs':float(20*np.log10(self.meter_peak)) if self.meter_peak else None,
                    'meter_rms_dbfs':float(10*np.log10(self.meter_square_sum/self.meter_count)) if self.meter_square_sum else None,
                    'output_meter_peak_dbfs':float(20*np.log10(self.output_meter_peak)) if self.output_meter_peak else None,
                    'output_overrange_samples':self.output_overrange_samples,
                    'meter_overrange_samples':self.meter_overrange_samples,
                    'gain_db':self.gain_db,'effective_buffer_frames':self.target}
            result['latency_resets']=self.latency_resets
            result['dropped_backlog_frames']=self.dropped_backlog_frames
            if reset_meter:
                self.meter_peak=self.meter_square_sum=self.meter_count=0
                self.output_meter_peak=0.0
                self.meter_overrange_samples=0
            return result
