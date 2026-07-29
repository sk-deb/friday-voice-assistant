# Installing FRIDAY as a Windows app

FRIDAY packages into a normal Windows application: `FridaySetup.exe` installs
her, Start Menu shortcuts launch her, and Add/Remove Programs uninstalls her.

There are two ways to get that installer. Neither can be done from Linux or
macOS — a Windows `.exe` has to be built on Windows.

## Option A — let GitHub Actions build it (no build tools needed)

Use this if you would rather not install anything but the app itself.

1. Go to the **Actions** tab of the repository
2. Select **Windows build** in the sidebar
3. Click **Run workflow** → **Run workflow**
4. Wait roughly 10–15 minutes
5. Download **FridaySetup** from the Artifacts section of the finished run
6. Unzip it and run `FridaySetup.exe`

Tagging a release does the same thing and attaches the installer to the release:

```bash
git tag v1.1.0
git push origin v1.1.0
```

## Option B — build it on your own PC

Use this if you want to rebuild after changing the code.

**You need:** Windows 10 or 11 (64-bit) and Python 3.10 or newer from python.org
with *Add python.exe to PATH* ticked. Inno Setup is optional and only needed for
the installer itself:

```powershell
winget install JRSoftware.InnoSetup
```

Then, from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

The script creates an isolated build environment, installs dependencies, runs
the test suite, freezes the app, smoke-tests the exe, and compiles the
installer. First run takes 10–20 minutes; later runs are much faster.

What you get:

```
dist\Friday\friday.exe            the app itself, portable
dist\installer\FridaySetup.exe    the installer
```

Useful flags:

```powershell
# exe only, skip Inno Setup
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1 -SkipInstaller

# start from scratch
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1 -Clean
```

## First run

1. Run `FridaySetup.exe`. **SmartScreen will warn you** that the publisher is
   unknown, because the installer is not code-signed. Choose *More info* →
   *Run anyway*. Signing needs a paid certificate.
2. The installer opens Notepad on your settings file at the end. Paste your key:

   ```
   GEMINI_API_KEY=your_key_here
   ```

   Get one free from Google AI Studio. Save and close.
3. Launch **Friday (type instead)** from the Start Menu first — it needs no
   microphone and proves the install works.
4. Then try **Friday (press to talk)**, and finally **Friday (always listening)**.

The **first voice run downloads the speech model** (about 500 MB by default) and
looks frozen for a few minutes. That happens once.

## Where things live

| What | Where |
|------|-------|
| The app | `C:\Program Files\Friday` |
| Settings (`.env`) | `%APPDATA%\Friday\.env` |
| Memory and conversation log | `%APPDATA%\Friday\friday.db` |
| Notes | `%APPDATA%\Friday\notes.md` |
| Log file | `%APPDATA%\Friday\friday.log` |
| Downloaded speech models | `%APPDATA%\Friday\models` |

The app folder stays read-only; everything that changes lives under `%APPDATA%`,
so FRIDAY works without administrator rights after installation. Uninstalling
asks before deleting your memory, notes and key, so reinstalling keeps them.

## Shortcuts you get

| Shortcut | Mode | What it does |
|----------|------|--------------|
| Friday (always listening) | `--mode wake` | Waits for the wake word |
| Friday (press to talk) | `--mode ptt` | Press Enter, then speak |
| Friday (type instead) | `--mode text` | Typed input, no microphone |
| Friday settings | — | Opens `.env` in Notepad |

Ticking *Start FRIDAY when I sign in* during setup adds always-listening mode to
your startup folder.

## Things that go wrong

**The window flashes and disappears.** Run it from a terminal to see the error:
`"C:\Program Files\Friday\friday.exe" --mode text`.

**"FRIDAY needs a Gemini API key".** The `.env` is missing or the key line is
empty. Start Menu → *Friday settings*.

**No microphone / audio errors.** Settings → Privacy & security → Microphone,
and allow desktop apps. Check the input device in Sound settings.

**The wake word never triggers.** Say "hey jarvis" clearly, then lower the
threshold: `FRIDAY_WAKE_THRESHOLD=0.4`.

**Non-English text prints as boxes.** The characters are fine, the console font
is not. Right-click the title bar → Properties → pick a font with wider coverage.

**Antivirus quarantines the exe.** Unsigned PyInstaller builds are a common false
positive. Add an exclusion for the install folder, or build it yourself with
Option B so nothing is downloaded.

**It answers in the wrong language.** See `docs/LANGUAGES.md` — narrowing
`FRIDAY_LANGUAGES` to the ones you speak fixes most cases.

More in `docs/TROUBLESHOOTING.md`.

## Why a folder build and not one file

PyInstaller can produce a single `.exe`. FRIDAY does not, on purpose: she bundles
CTranslate2, ONNX Runtime and NumPy, and a one-file build unpacks all of it to a
temporary folder on every single launch — several seconds of delay for an
assistant whose value is answering quickly. The installer hides the folder
anyway.
