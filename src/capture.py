# SPDX-License-Identifier: GPL-2.0-only
# HD300 USB parameters derived from Linux sound/usb/line6/podhd.c.
import argparse
from collections import Counter
from contextlib import closing
import ctypes
import json
from pathlib import Path
import time
import wave

import libusb_package
import usb1

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=10)
    args = parser.parse_args()
    if not 0 < args.seconds <= 120:
        parser.error('seconds must be between 0 and 120')
    usb1.loadLibrary(ctypes.CDLL(libusb_package.get_library_path()))
    stamp = time.strftime('%Y%m%d-%H%M%S')
    stats = {'format': '48000 Hz, stereo, signed 24-bit little-endian',
             'packet_lengths': Counter(), 'packet_status': Counter(), 'transfer_status': Counter()}
    chunks = []
    transfers = []
    running = True
    with usb1.USBContext() as ctx:
        dev = ctx.getByVendorIDAndProductID(0x0e41, 0x5057)
        if dev is None:
            raise SystemExit('HD300 not connected')
        with closing(dev.open()) as handle:
            previous_config = handle.getConfiguration()
            claimed = False
            try:
                if previous_config != 1:
                    handle.setConfiguration(1)
                handle.claimInterface(0)
                claimed = True
                handle.setInterfaceAltSetting(0, 5)
                def completed(transfer):
                    status = transfer.getStatus()
                    stats['transfer_status'][str(status)] += 1
                    if status == usb1.TRANSFER_COMPLETED:
                        for packet_status, data in transfer.iterISO():
                            stats['packet_status'][str(packet_status)] += 1
                            stats['packet_lengths'][str(len(data))] += 1
                            if packet_status == usb1.TRANSFER_COMPLETED and data:
                                chunks.append(bytes(data))
                    if running and status in (usb1.TRANSFER_COMPLETED, usb1.TRANSFER_TIMED_OUT):
                        transfer.submit()
                for _ in range(8):
                    transfer = handle.getTransfer(iso_packets=16)
                    transfer.setIsochronous(0x82, 300 * 16, callback=completed,
                                            timeout=2000, iso_transfer_length_list=[300] * 16)
                    transfers.append(transfer)
                    transfer.submit()
                started = time.monotonic()
                print('Capturing HD300 USB audio...', flush=True)
                while time.monotonic() - started < args.seconds:
                    ctx.handleEventsTimeout(0.05)
                stats['wall_seconds'] = time.monotonic() - started
            finally:
                running = False
                for transfer in transfers:
                    if transfer.isSubmitted():
                        transfer.cancel()
                deadline = time.monotonic() + 5
                while any(t.isSubmitted() for t in transfers) and time.monotonic() < deadline:
                    ctx.handleEventsTimeout(0.05)
                if any(t.isSubmitted() for t in transfers):
                    raise RuntimeError('USB transfers did not drain; unplug/replug HD300')
                if claimed:
                    try:
                        handle.setInterfaceAltSetting(0, 0)
                    finally:
                        handle.releaseInterface(0)
                # Leave the device idle, retaining its standard USB configuration.
    data = b''.join(chunks)
    stats['bytes'] = len(data)
    stats['frame_alignment_remainder'] = len(data) % 6
    stats['audio_seconds'] = len(data) / (48000 * 6)
    stats['nonzero_bytes'] = sum(b != 0 for b in data)
    if data and len(data) % 6 == 0:
        filename = ROOT / 'recordings' / f'hd300-{stamp}.wav'
        with wave.open(str(filename), 'wb') as wav:
            wav.setnchannels(2)
            wav.setsampwidth(3)
            wav.setframerate(48000)
            wav.writeframes(data)
        stats['wav'] = str(filename)
    (ROOT / 'logs' / f'capture-{stamp}.json').write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))
    return 0 if data and len(data) % 6 == 0 else 1

if __name__ == '__main__':
    raise SystemExit(main())
