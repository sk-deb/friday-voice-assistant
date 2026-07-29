# Tools

Tools are how FRIDAY does anything other than talk. They are plain Python callables handed to Gemini; the SDK builds the schema from type hints and docstrings, executes the call locally, and feeds the result back into the same turn.

## Built-in tools

| Tool | Signature | What it does |
| --- | --- | --- |
| `get_current_time` | `()` | Local date and time, spoken form |
| `get_machine_status` | `()` | Platform, CPU count, free disk |
| `open_application` | `(name)` | Launches a desktop app, per-platform |
| `open_url` | `(url)` | Opens a URL in the default browser |
| `search_the_web` | `(query)` | Opens a web search |
| `read_clipboard` | `()` | Reads clipboard text, capped at 4,000 chars |
| `write_clipboard` | `(text)` | Copies text to the clipboard |
| `run_shell_command` | `(command)` | Runs a shell command. **Disabled unless armed** |
| `remember_fact` | `(fact)` | Stores a durable fact about you |
| `forget_fact` | `(topic)` | Deletes facts matching a topic |
| `list_remembered_facts` | `()` | Reads back stored facts |
| `take_note` | `(text)` | Appends a timestamped line to `~/.friday/notes.md` |
| `read_recent_notes` | `(count=5)` | Reads the last few notes |

Remembered facts are injected into the system prompt at startup, so "remember I take my coffee black" survives restarts and shapes later answers.

---

## The tool contract

Five rules. Break them and the model behaves badly in ways that are hard to debug.

1. **Simple type hints only** - `str`, `int`, `bool`. The schema generator cannot express your dataclass.
2. **The docstring is the API description.** The model chooses tools based on it. Write it for the model, imperatively: *"Open a desktop application by name, for example 'chrome' or 'spotify'."*
3. **Return a short string meant to be spoken.** `"Opened Chrome."` not `{"status": "ok", "pid": 4192}`.
4. **Never raise.** Catch everything and return the failure as a sentence. A raised exception aborts the whole turn.
5. **Cap your output.** Long returns waste context and get read aloud. `MAX_TOOL_OUTPUT` is 4,000 characters.

---

## Adding a stateless tool

In `friday/tools/system.py`:

```python
def set_volume(percent: int) -> str:
    """Set the system output volume to a percentage from 0 to 100."""
    percent = max(0, min(100, percent))
    if platform.system() == "Darwin":
        subprocess.run(["osascript", "-e", f"set volume output volume {percent}"])
    else:
        return "Volume control is not implemented on this platform yet."
    return f"Volume set to {percent} percent."
```

Register it in `friday/tools/__init__.py`:

```python
from .system import set_volume

def build_toolset(settings, memory):
    tools = [
        ...
        set_volume,
    ]
```

That is all. No schema, no JSON, no registration decorator.

---

## Adding a stateful tool

Tools that need settings, credentials or the memory handle are built by a factory that closes over the dependency. This keeps tool bodies free of globals and makes them trivially testable.

```python
def make_calendar_tools(credentials) -> list[Callable[..., str]]:
    def list_todays_events() -> str:
        """List the events on the owner's calendar for today."""
        try:
            events = credentials.fetch_today()
        except Exception as exc:
            return f"I could not reach the calendar: {exc}"
        if not events:
            return "Nothing on the calendar today."
        return "; ".join(f"{e.time} {e.title}" for e in events[:5])

    return [list_todays_events]
```

Then extend `build_toolset`:

```python
tools.extend(make_calendar_tools(credentials))
```

`make_shell_tool`, `make_memory_tools` and `make_note_tools` all follow this shape - read them as reference implementations.

---

## Testing tools

`tests/test_tools.py` asserts that every registered tool is callable and has a docstring, which catches the most common mistake. Test behaviour directly against the factory:

```python
def test_volume_is_clamped(self):
    self.assertIn("100", set_volume(500))
```

Gating matters too. The shell tool has two tests: one proving it refuses when disarmed, one proving it works when explicitly allowed. Any tool with a safety gate should have both.

---

## Debugging tool selection

Run with `--verbose`. On startup the full registry is logged:

```
INFO friday.app Tools loaded: get_current_time, get_machine_status, open_application, ...
```

If the model refuses to call a tool you expect, the docstring is almost always the cause. Make it more specific and add an example of the argument. If the model calls the wrong tool, two descriptions overlap - sharpen the distinction between them.
