import ctypes
from contextlib import closing
import json
import libusb_package
import usb1

usb1.loadLibrary(ctypes.CDLL(libusb_package.get_library_path()))
with usb1.USBContext() as ctx:
    dev = ctx.getByVendorIDAndProductID(0x0e41, 0x5057)
    if dev is None:
        raise SystemExit('HD300 not connected')
    result = {'vid': '0e41', 'pid': '5057', 'speed': dev.getDeviceSpeed(), 'settings': []}
    for cfg in dev:
        for interface in cfg:
            for setting in interface:
                result['settings'].append({
                    'config': cfg.getConfigurationValue(),
                    'interface': setting.getNumber(), 'alt': setting.getAlternateSetting(),
                    'class': setting.getClass(),
                    'endpoints': [{'address': hex(ep.getAddress()), 'attributes': ep.getAttributes(),
                                   'max_packet': ep.getMaxPacketSize(), 'interval': ep.getInterval()}
                                  for ep in setting]})
    with closing(dev.open()) as handle:
        result['open'] = True
        result['configuration'] = handle.getConfiguration()
        try:
            handle.claimInterface(0)
            result['claim_interface_0'] = True
            result['current_alternate_setting'] = list(handle.controlRead(0x81, 10, 0, 0, 1))[0]
            handle.releaseInterface(0)
        except usb1.USBError as e:
            result['claim_interface_0'] = str(e)
    print(json.dumps(result, indent=2))
