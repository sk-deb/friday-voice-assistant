# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build recipe for FRIDAY on Windows.

Build with:
    pyinstaller packaging/friday.spec --noconfirm --clean

The result is ``dist/Friday/friday.exe`` - a folder build, not a single file.
That is deliberate: FRIDAY carries CTranslate2, ONNX Runtime and NumPy, so a
one-file exe would unpack hundreds of megabytes to a temp folder on every
launch and add seconds of startup delay to a program whose whole point is
answering fast.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = Path(SPECPATH).parent

# --------------------------------------------------------------- data files
# openWakeWord and faster-whisper ship .onnx / .tflite models and metadata
# inside their packages. PyInstaller only bundles Python modules unless the
# data files are collected explicitly, and missing them fails at runtime.
# webrtcvad is a single extension module rather than a package, so it has no
# data files to collect - asking for them only produced a warning.
datas = []
for package in ("openwakeword", "faster_whisper", "pyttsx3"):
    try:
        datas += collect_data_files(package)
    except Exception as exc:  # pragma: no cover - build time diagnostics
        print(f"[friday.spec] no data files collected for {package}: {exc}")

# sounddevice itself is a plain module; the PortAudio DLL it needs lives in the
# separate _sounddevice_data package, which is the one worth collecting.
binaries = []
for package in ("ctranslate2", "onnxruntime", "_sounddevice_data"):
    try:
        binaries += collect_dynamic_libs(package)
    except Exception as exc:  # pragma: no cover - build time diagnostics
        print(f"[friday.spec] no binaries collected for {package}: {exc}")

# Ship a starter configuration next to the exe so the installed app is
# self-documenting.
for extra in ("README.md", ".env.example", "LICENSE"):
    candidate = ROOT / extra
    if candidate.is_file():
        datas.append((str(candidate), "."))

for doc in sorted((ROOT / "docs").glob("*.md")):
    datas.append((str(doc), "docs"))

# Optional: any Piper voices the builder has already downloaded get bundled.
voices = ROOT / "voices"
if voices.is_dir():
    for voice in voices.iterdir():
        if voice.is_file():
            datas.append((str(voice), "voices"))

# ------------------------------------------------------------ hidden imports
# Everything FRIDAY imports lazily inside functions is invisible to
# PyInstaller's static analysis, so each one must be named here.
hiddenimports = [
    "friday",
    "friday.app",
    "friday.config",
    "friday.i18n",
    "friday.llm",
    "friday.memory",
    "friday.stt",
    "friday.tts",
    "friday.audio.ears",
    "friday.audio.wake",
    "friday.tools",
    "friday.tools.knowledge",
    "friday.tools.language",
    "friday.tools.system",
    # Speech in
    "faster_whisper",
    "ctranslate2",
    "tokenizers",
    "onnxruntime",
    "openwakeword",
    "openwakeword.model",
    "webrtcvad",
    "sounddevice",
    "numpy",
    # Speech out - pyttsx3 picks its driver at runtime by name
    "pyttsx3",
    "pyttsx3.drivers",
    "pyttsx3.drivers.sapi5",
    "comtypes",
    "comtypes.client",
    "comtypes.stream",
    "win32com",
    "win32com.client",
    # Thinking
    "google.genai",
    "google.genai.types",
    # Odds and ends
    "pyperclip",
    "dotenv",
    "sqlite3",
]

excludes = [
    # Large scientific and GUI stacks that get pulled in transitively but are
    # never used. Excluding them keeps the build roughly a third smaller.
    "tkinter",
    "matplotlib",
    "scipy",
    "pandas",
    "PyQt5",
    "PySide6",
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
    "torch",
    "torchaudio",
    "tensorflow",
]


a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    # Our own hooks win over PyInstaller's bundled ones. packaging/hooks holds
    # a replacement for the contrib webrtcvad hook, which otherwise aborts the
    # build when webrtcvad-wheels is installed instead of webrtcvad.
    hookspath=[str(ROOT / "packaging" / "hooks")],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "packaging" / "runtime_hook.py")],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

icon = ROOT / "packaging" / "friday.ico"

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="friday",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # FRIDAY prints the conversation; a console is the interface
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon) if icon.is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Friday",
)
