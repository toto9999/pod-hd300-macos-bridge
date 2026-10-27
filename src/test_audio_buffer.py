import unittest
import numpy as np
from audio_buffer import AudioBuffer

class AudioBufferTests(unittest.TestCase):
    def test_pcm24_extremes_and_channel_order(self):
        samples = [-(1 << 23), (1 << 23) - 1, -1, 0, 1, 42]
        raw = b''.join(x.to_bytes(3, 'little', signed=True) for x in samples)
        fifo = AudioBuffer(capacity=32, target=3)
        fifo.push_pcm24(raw)
        np.testing.assert_array_equal(fifo.data[:3],
                                     np.array(samples, dtype=np.float32).reshape(3, 2) / 8388608)
        with self.assertRaises(ValueError):
            fifo.push_pcm24(b'bad')

    def test_wrap_preserves_frame_and_channel_order(self):
        fifo = AudioBuffer(capacity=256, target=96)
        fifo.read = fifo.write = 224
        history = np.column_stack([np.arange(-16, 0), -np.arange(-16, 0)]).astype(np.float32)
        fifo.data[(fifo.read+np.arange(-16,0))%fifo.capacity] = history
        samples = np.column_stack([np.arange(96), -np.arange(96)]).astype(np.float32)
        fifo.push(samples)
        output = np.empty((32, 2), dtype=np.float32)
        fifo.render(output)
        np.testing.assert_allclose(output, samples[:32], atol=0.00001)

    def test_underflow_silences_and_overflow_bounds_latency(self):
        fifo = AudioBuffer(capacity=32, target=8)
        output = np.ones((8, 2), dtype=np.float32)
        fifo.render(output)
        self.assertFalse(output.any())
        fifo.push(np.ones((24, 2), dtype=np.float32))
        fifo.push(np.full((24, 2), 2, dtype=np.float32))
        self.assertEqual(fifo.snapshot()['queued_frames'], 32)
        self.assertEqual(fifo.snapshot()['overflows'], 1)
        fifo.render(np.empty((8, 2), dtype=np.float32))
        fifo.render(np.empty((32, 2), dtype=np.float32))
        self.assertEqual(fifo.snapshot()['underruns'], 1)

    def test_44100_output_resamples_48k_tone(self):
        fifo = AudioBuffer(capacity=96000, target=48000)
        t = np.arange(48000) / 48000
        tone = np.sin(2 * np.pi * 1000 * t).astype(np.float32)
        fifo.push(np.column_stack([tone, tone]))
        output = np.empty((4410, 2), dtype=np.float32)
        fifo.render(output, 48000 / 44100)
        frequency = np.argmax(abs(np.fft.rfft(output[:, 0]))) * 44100 / len(output)
        self.assertEqual(frequency, 1000)
        self.assertLess(abs(np.max(output) - 1), 0.01)
        self.assertEqual(fifo.snapshot()['underruns'], 0)

    def test_downsampling_filters_above_output_nyquist(self):
        fifo = AudioBuffer(capacity=96000, target=48000)
        t = np.arange(48000) / 48000
        tone = np.sin(2*np.pi*23500*t).astype(np.float32)
        fifo.push(np.column_stack([tone,tone]))
        output = np.empty((4410,2),dtype=np.float32)
        fifo.render(output,48000/44100)
        self.assertLess(float(np.sqrt(np.mean(output[64:]**2))),0.04)

    def test_gain_ramps_without_a_full_scale_step(self):
        fifo=AudioBuffer(capacity=96000,target=48000)
        fifo.push(np.full((48000,2),0.1,dtype=np.float32))
        fifo.configure(gain_db=6)
        output=np.empty((128,2),dtype=np.float32)
        fifo.render(output)
        self.assertLess(float(np.max(output)),0.105)
        for _ in range(200):
            fifo.render(output)
        self.assertGreater(float(np.min(output)),0.19)
        self.assertEqual(fifo.snapshot()['output_overrange_samples'],0)

    def test_meter_reset_preserves_lifetime_counts(self):
        fifo=AudioBuffer()
        fifo.push(np.full((96,2),0.5,dtype=np.float32))
        first=fifo.snapshot(reset_meter=True)
        self.assertAlmostEqual(first['meter_peak_dbfs'],-6.0206,places=3)
        self.assertIsNone(fifo.snapshot()['meter_peak_dbfs'])
        self.assertAlmostEqual(fifo.snapshot()['input_peak_dbfs'],-6.0206,places=3)

    def test_stalled_consumer_discards_stale_audio(self):
        fifo=AudioBuffer(capacity=96000,target=256)
        fifo.push(np.full((36000,2),0.25,dtype=np.float32))
        output=np.empty((128,2),dtype=np.float32)
        fifo.render(output)
        state=fifo.snapshot()
        self.assertEqual(state['latency_resets'],1)
        self.assertEqual(state['dropped_backlog_frames'],36000-256)
        self.assertLess(state['queued_frames'],256)
        self.assertLess(state['queue_delay_ms'],6)
        self.assertEqual(output[0,0],0)
        self.assertAlmostEqual(float(output[-1,0]),0.25,places=5)

    def test_clock_drift_does_not_require_a_large_fifo_offset(self):
        fifo=AudioBuffer(target=128)
        fifo.prepare(48000/44100)
        output=np.empty((64,2),dtype=np.float32)
        usb_time=0.001
        audio_time=64/44100
        produced=0
        observed=[]
        while min(usb_time,audio_time)<30:
            if usb_time<=audio_time:
                total=int(usb_time*48000*1.0002)
                fifo.push(np.zeros((total-produced,2),dtype=np.float32))
                produced=total;usb_time+=0.001
            else:
                fifo.render(output,48000/44100)
                if audio_time>25:
                    observed.append(fifo.write-fifo.read)
                audio_time+=64/44100
        self.assertEqual(fifo.underruns,0)
        self.assertEqual(fifo.latency_resets,0)
        self.assertLess(float(np.mean(observed)),192)

if __name__ == '__main__':
    unittest.main()
