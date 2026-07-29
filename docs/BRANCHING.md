# Branching workflow

Every change to this repository lands on its own branch, is described in a pull request, and is merged into `main`. Nothing is committed directly to `main`. The branch history is therefore a readable record of how FRIDAY was built, one increment at a time.

## Branch naming

```
<type>/<NNN>-<short-kebab-summary>
```

`NNN` is a zero-padded sequence number that increments across the whole repository, so branches sort chronologically.

| Type | Use for |
| --- | --- |
| `feat` | New capability |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `perf` | Latency or resource improvements |
| `refactor` | Restructuring with no behaviour change |
| `chore` | Tooling, CI, dependencies |

Examples:

```
feat/001-core-voice-pipeline
feat/002-custom-friday-wake-word
perf/003-parallel-stt-and-tts-warmup
fix/004-clipped-first-syllable
docs/005-latency-benchmarks
```

## The loop

```bash
git checkout main && git pull
git checkout -b feat/002-custom-friday-wake-word

# ... work ...

python -m unittest discover -s tests -t .
ruff check .

git add -A
git commit -m "feat: train and load a custom Friday wake word"
git push -u origin feat/002-custom-friday-wake-word
```

Then open a pull request against `main`, let CI pass, and merge. Keep the branch after merging - it is part of the history this repository is meant to preserve.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org). Subject in the imperative mood, under 72 characters.

```
feat: stream replies sentence by sentence
fix: prepend pre-roll audio so the first syllable survives
perf: disable Gemini thinking to cut first-token latency
docs: document the wake-word training path
```

Body, when the change deserves one, explains *why* rather than *what* - the diff already covers what.

## Pull requests

One branch, one concern. If a PR needs the word "also" in its description, it should have been two branches.

Every PR states what changed, why, how it was verified, and whether configuration or documentation had to move with it. The template in `.github/PULL_REQUEST_TEMPLATE.md` enforces this.

## Releases

`main` is always runnable. Tag it when a meaningful set of changes has accumulated:

```bash
git tag -a v1.1.0 -m "Custom wake word, Piper streaming"
git push origin v1.1.0
```

Versions follow [Semantic Versioning](https://semver.org): breaking configuration changes bump major, new capability bumps minor, fixes bump patch. Record every release in [CHANGELOG.md](../CHANGELOG.md).
