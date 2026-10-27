# Third-party components and licenses

The project-owned bridge, controller, scripts and tests are GPL-2.0-only unless a file states otherwise.
See [LICENSE](LICENSE). Vendored components retain their original copyright notices and licenses.

## Linux Line 6 reference sources — GPL-2.0-only

`vendor/linux-line6/` contains reference sources from
[`torvalds/linux/sound/usb/line6`](https://github.com/torvalds/linux/tree/master/sound/usb/line6).
These files document the HD300 USB ID, alternate setting, endpoints and packed PCM24 format.
They are not compiled into a macOS kernel driver. Original notices and license text are preserved.
Retrieved file hashes and URLs are recorded in `vendor/SOURCES.json`.

## BlackHole HAL plug-in — GPL-3.0

[`ExistentialAudio/BlackHole`](https://github.com/ExistentialAudio/BlackHole) is a separate
Core Audio HAL component by Existential Audio Inc. It is not relicensed by this repository's LICENSE.
The pinned commit is recorded in `vendor/blackhole-revision.txt` and the Git submodule.
The driver is built from upstream C source using the customization macros in `src/build_driver.py`.
The binary driver includes upstream's GPL-3.0 license in `Contents/Resources/BlackHole-GPL-3.0.txt`.
Release kits include the corresponding BlackHole source and license beside the bridge source.

## Runtime dependencies

Runtime packages are installed by Setup.command into the local `.venv`; that environment and
its dependencies are not uploaded to GitHub or bundled in the release archive.

| Package | Upstream license |
| --- | --- |
| libusb1 (python-libusb1) | LGPL-2.1-or-later |
| libusb-package | Apache-2.0 wrapper; bundled libusb retains its LGPL-2.1-family license |
| sounddevice | MIT |
| PortAudio (bundled with sounddevice) | MIT-style PortAudio license |
| NumPy | BSD-3-Clause plus bundled 0BSD/MIT/Zlib/CC0-1.0 notices |
| SciPy | BSD-3-Clause plus bundled dependency notices |
| CFFI / pycparser | MIT-0 / BSD-3-Clause |
| importlib-resources | Apache-2.0 |
| uv setup tool | Apache-2.0 OR MIT |
| CPython setup runtime | PSF license |

The upstream package metadata and included license files are the authoritative notices for each
downloaded version. Python, uv and the package cache remain inside the selected application folder.

Line 6, POD, GarageBand and macOS are their respective owners' trademarks. This is an independent,
experimental project and is not an official Line 6 or Apple driver.
