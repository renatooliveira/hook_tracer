# Hook Tracer

A developer add-on for observing Anki's Python hooks and filters. The headless
core, add-on lifecycle, and live stream dock with details and a catalog are
implemented. See [spec.md](spec.md) and [tasks.md](tasks.md) for the
implementation plan.

## Development

Install [uv](https://docs.astral.sh/uv/), then run:

```sh
uv sync --locked
uv run pytest
uv run mypy
uv run ruff check .
uv run ruff format --check .
```

The environment uses Python 3.12, Anki/aqt 26.9.3, and Qt 6. `uv.lock` records
resolved tool and dependency versions. Use `uv run ruff format .` to format code.
Mypy checks the add-on strictly; upstream contract probes in `tests/` are runtime
tests, not part of the strict typing scope. Tests do not use a real Anki profile.
GUI discovery runs in a separate offscreen process; core imports remain Qt-free.
To print real pylib hook events from a disposable collection, run
`uv run python -m examples.trace_note`.

See [compatibility decisions](docs/compatibility.md) for verified upstream
behavior, import-order requirements, and platform limitations.

## Anki console and stream panel (26.9.3 only)

Symlink the `hook_tracer/` package directory into Anki's `addons21` directory.
Find the exact directory by running `aqt.mw.pm.addonFolder()` in Anki's debug
console (the add-ons directory is shared by profiles in that Anki installation):

```sh
ln -s /absolute/path/to/hook_tracer/hook_tracer /path/to/Anki2/addons21/hook_tracer
```

Restart Anki (use a disposable profile). **Tools > Hook Tracer: Record** toggles
recording; it starts paused unless `trace_on_startup` is set to `true` in the
add-on config. **Tools > Hook Tracer** opens the reusable live stream dock.
Its Pause/Resume, Clear, hook-name substring/regex filter, and no-callbacks
filter act on the buffered stream. Invalid regexes show an error instead of
interrupting recording. A row's **Mute recording for selected hook** action
stops new events for that hook from entering the buffer or debug console; use
the **Session mutes** dropdown to unmute even if no rows remain. Session mutes
are not saved across restarts yet. A view filter, unlike muting, does not
prevent buffer eviction or debug-console spam. Selecting a row shows stored
argument reprs, callback owners, filter input/output and errors in the detail
pane. The Catalog tab lists discovered hooks, current registrations and
session fire counts, sorted by callback count. Counts include attempted fires
(including callbacks that raise) only while recording is on and the hook is
unmuted and not tracer-suppressed. Pausing and muting do not increment counts;
clearing the buffer does not reset them. The catalog refreshes every second
while its tab is open.

Open Anki's debug console (Ctrl+:); its log displays retained hook events and
continues updating every 250 ms while open. Close the console to stop output;
recording can continue in the background. To stop/unpatch entirely during a
session, run `import hook_tracer; hook_tracer.stop()` in the
console. Restart Anki or call `hook_tracer.start(aqt.mw)` to re-enable it.

Startup coverage begins only when Anki imports this package. Anki 26.9.3 loads
add-ons by sorted directory name in `setupAddons()` after creating the main
window, so earlier core/UI hooks and hooks fired by alphabetically earlier
add-ons cannot be captured. Renaming the folder to load first is not a
supported guarantee across Anki versions. The Tools menu is already available
when this add-on loads. The generated legacy delegation is still executed but
not recorded as a separate event.

**Manual smoke checklist (still required on a real Anki install):** turn on
recording, open the debug console, review several cards, and confirm
`gui.reviewer_did_answer_card` and other reviewer hooks appear without a change
in reviewer behavior or errors. Toggle recording off/on; check that paused
reviews emit no new events. Stop/unpatch and check the reviewer still works.
Before choosing muted defaults, count the most frequent hook names in a
representative review session from the bounded snapshot (up to 5000 events):

```python
from collections import Counter
import hook_tracer

Counter(e.hook for e in hook_tracer.start(aqt.mw).recorder.snapshot()).most_common(20)
```

This is a sample, not a full-session count after buffer eviction. A real Anki
smoke test, a 100-card review-session responsiveness check, and noise
measurement remain outstanding; automated offscreen Qt and real pylib
`Collection` tests are not a substitute for checking add-on attribution and
dynamic registrations in a live Anki session.

## Layout

- `hook_tracer/__init__.py`: add-on startup, Tools toggle, console feed and shutdown
- `hook_tracer/core/`: pure-Python discovery, recording, patching, and ownership
- `hook_tracer/ui/`: stream dock, bounded table model, details, and catalog
- `tests/`: upstream compatibility probes and headless tests

## Contribution workflow

Use one branch and PR per phase, and one commit per checklist item. Update the
corresponding checkbox in the same commit. Keep PRs unmerged until reviewed.
