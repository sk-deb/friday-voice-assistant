# -*- coding: utf-8 -*-
"""Local override for the bundled pyinstaller-hooks-contrib webrtcvad hook.

On Windows we install ``webrtcvad-wheels`` rather than ``webrtcvad``, because
the original package ships only an sdist and needs a C++ compiler to build.
The wheel provides the very same importable ``webrtcvad`` module, but it
registers its distribution metadata under the name ``webrtcvad-wheels``.

The hook shipped with pyinstaller-hooks-contrib calls
``copy_metadata("webrtcvad")`` unconditionally. With the wheel installed that
raises ``PackageNotFoundError``, which PyInstaller reports as
``ImportErrorWhenRunningHook`` and which kills the build during analysis -
before a single module has been collected.

Hooks found in the spec's ``hookspath`` take precedence over the bundled ones,
so this file replaces that behaviour: try both distribution names, and treat
missing metadata as a note rather than a fatal error. Nothing in FRIDAY reads
webrtcvad's metadata at runtime - it only calls into the extension module - so
an empty result here is harmless.
"""

from PyInstaller.utils.hooks import copy_metadata

datas = []

for distribution in ("webrtcvad", "webrtcvad-wheels"):
    try:
        datas += copy_metadata(distribution)
    except Exception:  # pragma: no cover - build time diagnostics
        continue

if not datas:
    print("[hook-webrtcvad] no distribution metadata found; continuing without it")
