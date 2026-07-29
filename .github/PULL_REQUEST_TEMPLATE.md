## What changed

<!-- One or two sentences. If you need the word "also", split this into two PRs. -->

## Why

<!-- The problem this solves, or the capability it adds. -->

## How it was verified

- [ ] `python -m unittest discover -s tests -t .` passes
- [ ] `ruff check .` and `ruff format --check .` pass
- [ ] Tested by hand in `--mode text`
- [ ] Tested by hand with a microphone (`--mode ptt` or `--mode wake`)

<!-- Note any measured latency change. -->

## Documentation

- [ ] `docs/CONFIGURATION.md` and `.env.example` updated (new settings)
- [ ] `docs/TOOLS.md` updated (new tools)
- [ ] `requirements.txt`, `pyproject.toml` and `scripts/doctor.py` updated (new dependencies)
- [ ] `docs/ARCHITECTURE.md` updated (structural change)
- [ ] `CHANGELOG.md` updated (user-visible change)

## Safety

- [ ] No secrets, keys or personal data in the diff
- [ ] Any new tool follows the contract in `docs/TOOLS.md` and cannot raise
- [ ] Any destructive capability is gated behind an explicit setting
