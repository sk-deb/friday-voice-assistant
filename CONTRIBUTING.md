# Contributing

This is a personal assistant, but it is built like a real project: branch per change, tests that run without hardware, and documentation that keeps up.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env      # add your Gemini key
python scripts/doctor.py
```

## Before every commit

```bash
python -m unittest discover -s tests -t .
ruff check .
ruff format --check .
```

All three must pass. CI runs the same commands on Python 3.10, 3.11 and 3.12.

## Branching

One branch per change, named `<type>/<NNN>-<summary>`, merged into `main` through a pull request. Never commit to `main` directly. The full convention, including commit message format and release tagging, is in [docs/BRANCHING.md](docs/BRANCHING.md).

## Code conventions

- **Lazy imports for heavy dependencies.** `faster_whisper`, `sounddevice`, `openwakeword`, `google.genai` and `pyttsx3` are imported inside the function or constructor that needs them, never at module top level. This is what keeps the test suite and `--mode text` runnable on a machine with no audio stack.
- **Specific unavailability errors.** When a dependency is missing, raise a `*UnavailableError` whose message contains the exact `pip install` line.
- **Configuration in one place.** New settings go in `friday/config.py` as a field with a default and an env override. No module other than `config.py` reads `os.environ`.
- **Tools follow the contract.** Simple type hints, a docstring written for the model, a short spoken-form return string, and no raised exceptions. See [docs/TOOLS.md](docs/TOOLS.md).
- **Comments explain why.** The code already says what. Comment the non-obvious decision - why the pre-roll buffer exists, why the mic is muted while speaking.
- **Line length 88**, enforced by `ruff format`.

## Tests

The suite uses only `unittest` from the standard library, deliberately: no test run should require installing a test framework, a microphone or an API key.

- Use `tempfile.TemporaryDirectory` for anything touching disk.
- Use `unittest.mock.patch.dict(os.environ, ...)` for configuration tests.
- Anything with a safety gate needs two tests: refused when disarmed, working when armed.
- Never make a network call in a test.

## Documentation

A change that adds a setting, a tool or a dependency is not finished until the matching document is updated:

| Change | Update |
| --- | --- |
| New setting | `docs/CONFIGURATION.md` and `.env.example` |
| New tool | `docs/TOOLS.md` |
| New dependency | `requirements.txt`, `pyproject.toml`, `scripts/doctor.py` |
| Structural change | `docs/ARCHITECTURE.md` |
| New failure mode | `docs/TROUBLESHOOTING.md` |
| Anything user-visible | `CHANGELOG.md` |

## Reporting problems

Include the output of `python scripts/doctor.py`, your OS and Python version, the relevant lines from `~/.friday/friday.log` at `--verbose`, and what you expected to happen. Never paste your API key.
