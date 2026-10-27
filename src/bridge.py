# SPDX-License-Identifier: GPL-2.0-only
"""HD300 USB PCM -> a separately installed CoreAudio loopback output device."""
import argparse
from collections import Counter, deque
from contextlib import closing
import ctypes
import fcntl
import json
import os
from pathlib import Path
import signal
import time
import wave

import libusb_package
import sounddevice as sd
import usb1
from audio_buffer import AudioBuffer, prioritize_usb_thread
import settings
from latency_policy import LatencyPolicy

ROOT = Path(__file__).resolve().parents[1]
DEVICE = 'POD HD300 USB Bridge 2ch'
shutdown_requested = False

def publish_status(snapshot):
    statusfile = ROOT / 'logs/bridge-status.json.tmp'
    statusfile.write_text(json.dumps({**snapshot,'updated_at':time.time()},indent=2))
    statusfile.replace(ROOT / 'logs/bridge-status.json')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=0, help='0 means until Ctrl+C')
    parser.add_argument('--list-devices', action='store_true')
    parser.add_argument('--diagnostic', action='store_true', help='Save the last 10 seconds of raw USB input on stop')
    args = parser.parse_args()
    if args.list_devices:
        print(sd.query_devices())
        return 0
    if args.seconds < 0:
        parser.error('seconds cannot be negative')
    devices = sd.query_devices()
    matches = [i for i, d in enumerate(devices) if d['name'] == DEVICE and d['max_output_channels'] >= 2]
    if len(matches) != 1:
        raise SystemExit('POD HD300 USB Bridge 2ch is not installed/loaded. Run Install Bridge.command first.')
    index = matches[0]
    # Follow the HAL's current rate, including GarageBand's usual 44.1 kHz.
    output_rate = devices[index]['default_samplerate']
    sd.check_output_settings(device=index, channels=2, dtype='float32', samplerate=output_rate)
    current_settings=settings.load()
    fifo = AudioBuffer(target=current_settings['target'])
    fifo.configure(gain_db=current_settings['gain_db'])
    fifo.prepare(48000.0/output_rate)
    stats = {'pid': os.getpid(), 'usb_bytes': 0, 'usb_packet_status': Counter(), 'audio_callback_status': Counter(),
             'output_sample_rate': output_rate, 'output_device': DEVICE,
             'buffer_target_frames':current_settings['target'],'profile':current_settings['profile'],
             'usb_packets_per_transfer':1,'audio_block_frames':64,
             'resampler':'32-tap windowed-sinc, 1024 phases'}
    stats['usb_thread_priority_result']=prioritize_usb_thread()
    running = True
    failure = None
    def stop(signum, frame):
        global shutdown_requested
        nonlocal running
        shutdown_requested = True
        running = False
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, stop)
    def output_callback(outdata, frames, timing, status):
        if status:
            stats['audio_callback_status'][str(status)] += 1
        fifo.render(outdata, 48000.0 / output_rate)
    usb1.loadLibrary(ctypes.CDLL(libusb_package.get_library_path()))
    stamp = time.strftime('%Y%m%d-%H%M%S')
    pidfile = ROOT / 'logs/bridge.pid'
    lockfile = (ROOT / 'logs/bridge.lock').open('a')
    try:
        fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lockfile.close()
        raise SystemExit('Another bridge is running; use Stop Bridge.command first.')
    pidfile.write_text(str(os.getpid()))
    started = time.monotonic()
    transfers = []
    diagnostic=deque()
    diagnostic_bytes=0
    try:
        with usb1.USBContext() as ctx:
            dev = ctx.getByVendorIDAndProductID(0x0e41, 0x5057)
            if dev is None:
                raise RuntimeError('HD300 is not connected')
            with closing(dev.open()) as handle:
                claimed = False
                try:
                    if handle.getConfiguration() != 1:
                        handle.setConfiguration(1)
                    handle.claimInterface(0)
                    claimed = True
                    handle.setInterfaceAltSetting(0, 5)
                    def received(transfer):
                        nonlocal running, failure, diagnostic_bytes
                        status = transfer.getStatus()
                        if running and status == usb1.TRANSFER_COMPLETED:
                            packets = []
                            for packet_status, data in transfer.iterISO():
                                stats['usb_packet_status'][str(packet_status)] += 1
                                if packet_status == usb1.TRANSFER_COMPLETED and data:
                                    if len(data) % 6:
                                        failure = 'Received a misaligned PCM24 packet'
                                        running = False
                                        return
                                    packets.append(bytes(data))
                            if packets:
                                raw = b''.join(packets)
                                stats['usb_bytes'] += len(raw)
                                if args.diagnostic:
                                    diagnostic.append(raw)
                                    diagnostic_bytes += len(raw)
                                    while diagnostic_bytes > 48000*6*10:
                                        diagnostic_bytes -= len(diagnostic.popleft())
                                fifo.push_pcm24(raw)
                        elif running and status != usb1.TRANSFER_CANCELLED:
                            failure = 'USB transfer failed: ' + str(status)
                            running = False
                        if running and status == usb1.TRANSFER_COMPLETED:
                            try:
                                transfer.submit()
                            except usb1.USBError as exc:
                                failure = str(exc)
                                running = False
                    with sd.OutputStream(device=index, channels=2, samplerate=output_rate,
                                         dtype='float32', blocksize=64, latency='low',
                                         callback=output_callback) as stream:
                        stats['coreaudio_output_latency_ms'] = stream.latency * 1000
                        for _ in range(8):
                            t = handle.getTransfer(iso_packets=1)
                            t.setIsochronous(0x82, 300, callback=received, timeout=2000,
                                             iso_transfer_length_list=[300])
                            transfers.append(t)
                            t.submit()
                        print('HD300 USB -> ' + DEVICE + ': live. Stop with Ctrl+C.', flush=True)
                        print('GarageBand input: ' + DEVICE + '; output: speakers/headphones.', flush=True)
                        last_report = 0
                        published_running = False
                        last_settings_check = 0
                        policy=LatencyPolicy(time.monotonic(),fifo.underruns)
                        while running and (not args.seconds or time.monotonic() - started < args.seconds):
                            try:
                                ctx.handleEventsTimeout(0.002)
                            except usb1.USBErrorInterrupted:
                                continue
                            if not stream.active:
                                raise RuntimeError('CoreAudio stream stopped; restart bridge after selecting GarageBand input')
                            now=time.monotonic()
                            if now-last_settings_check>=0.25:
                                last_settings_check=now
                                try:
                                    updated=settings.load()
                                    if updated['profile']!=current_settings['profile']:
                                        fifo.configure(target=updated['target'])
                                        policy=LatencyPolicy(now,fifo.underruns)
                                    fifo.configure(gain_db=updated['gain_db'])
                                    current_settings=updated
                                    stats['profile']=updated['profile']
                                    stats['buffer_target_frames']=updated['target']
                                    stats.pop('settings_error',None)
                                except (ValueError,OSError) as exc:
                                    stats['settings_error']=str(exc)
                                target=policy.update(fifo.underruns,fifo.target,current_settings['target'],now)
                                if target!=fifo.target:
                                    fifo.configure(target=target)
                                    stats['automatic_buffer_adjustments']=stats.get('automatic_buffer_adjustments',0)+1
                            flowing = stats['usb_bytes'] > 0 and fifo.ready
                            if (flowing and not published_running) or time.monotonic() - last_report >= 0.25:
                                last_report = time.monotonic()
                                snapshot = {**stats, **fifo.snapshot(reset_meter=True), 'elapsed': last_report - started,
                                            'state':'running' if flowing else 'starting'}
                                publish_status(snapshot)
                                published_running = published_running or flowing
                        running = False
                finally:
                    running = False
                    for t in transfers:
                        if t.isSubmitted():
                            t.cancel()
                    deadline = time.monotonic() + 5
                    while any(t.isSubmitted() for t in transfers) and time.monotonic() < deadline:
                        try:
                            ctx.handleEventsTimeout(0.05)
                        except usb1.USBErrorInterrupted:
                            continue
                    if any(t.isSubmitted() for t in transfers):
                        raise RuntimeError('USB cancellation did not drain; unplug HD300')
                    if claimed:
                        try:
                            handle.setInterfaceAltSetting(0, 0)
                        finally:
                            handle.releaseInterface(0)
    except Exception as exc:
        failure = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        stats.update(fifo.snapshot())
        if diagnostic:
            with wave.open(str(ROOT/'recordings/usb-diagnostic.wav'),'wb') as wav:
                wav.setnchannels(2);wav.setsampwidth(3);wav.setframerate(48000)
                wav.writeframes(b''.join(diagnostic))
        stats['elapsed_seconds'] = time.monotonic() - started
        stats['failure'] = failure
        stats['state'] = 'failed' if failure else 'stopped'
        (ROOT / 'logs' / f'bridge-{stamp}.json').write_text(json.dumps(stats, indent=2))
        publish_status(stats)
        if pidfile.exists() and pidfile.read_text() == str(os.getpid()):
            pidfile.unlink()
        lockfile.close()
        print(json.dumps(stats, indent=2))
    return 1 if failure else 0

def run_with_recovery():
    consecutive_failures = 0
    while True:
        attempt_started = time.monotonic()
        try:
            code = main()
        except Exception as exc:
            print(f'Bridge attempt failed: {type(exc).__name__}: {exc}',flush=True)
            code = 1
        if not code or shutdown_requested:
            return code
        consecutive_failures = 1 if time.monotonic()-attempt_started >= 60 else consecutive_failures+1
        if consecutive_failures >= 3:
            print('Three consecutive connection failures; stopped. Reconnect HD300 then run Start Bridge.command.',flush=True)
            return 1
        print('Recovering USB/CoreAudio connection in 1 second...',flush=True)
        time.sleep(1)
        if shutdown_requested:
            return 0

if __name__ == '__main__':
    raise SystemExit(run_with_recovery())
