# Release procedure

Releases are experimental until independently qualified on the claimed hardware and OS versions.
Do not publish local recordings, logs, `.venv`, downloaded Python, caches or personal `settings.json`.

## Build without touching an active installation

```sh
export HD300_BUILD_DIR="$PWD/build/release-build"
export HD300_LOG_DIR="$PWD/logs/release-build"
.venv/bin/python src/build_all.py
.venv/bin/python -m unittest discover -s src -p 'test_*.py'
```

The BlackHole submodule revision must match `vendor/blackhole-revision.txt`.
The separate build directory prevents replacement of binaries currently in use by the local bridge.
The build does not install or activate a driver. The owner must use the installer for an actual installation.

## Package

After reviewing and committing the sources:

```sh
.venv/bin/python src/package_release.py
```

This generates `build/releases/pod-hd300-macos-bridge-VERSION-arm64.zip`, a standalone HAL installer,
and `SHA256SUMS.txt`. The ZIP contains tracked project sources, complete pinned BlackHole sources,
license notices, setup scripts and the selected native artifacts from `HD300_BUILD_DIR`.
It contains neither a Python environment nor user data. Setup.command downloads the local runtime
and pinned packages after the user extracts the kit.

## Qualification scope

- Run the unit suite and native signature checks.
- Exercise Setup.command in a freshly extracted kit, with caches and Python kept inside that kit.
- Verify USB detection from that environment while the active receiver is stopped.
- Inspect package payloads and archive paths for accidental files and absolute installation paths.
- Keep live hardware observations distinct from fresh-unit, long-session or cross-Mac qualification.
- Publish as a GitHub **prerelease** and state the tested macOS/device and known limitations.

Ad-hoc signatures are not Developer ID signatures or Apple notarization. No developer identity,
certificate, private key or signing credential is included. Do not claim notarization.

## Licensing

The root license does not replace the separate BlackHole GPL-3.0 license.
Always include the exact corresponding BlackHole source and its license with binary release kits.
Keep the vendored Linux files, copyright headers, notices and source hashes intact.
