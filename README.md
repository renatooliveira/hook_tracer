# Hook Tracer

A developer add-on for observing Anki's Python hooks and filters.

## Installation

Supported target: **Anki 26.9.3** (Python 3.12, Qt 6). Symlink this checkout's
`hook_tracer/` package into Anki's shared `addons21` directory. In Anki's debug
console, `aqt.mw.pm.addonFolder()` prints the exact destination:

```sh
ln -s /absolute/path/to/hook_tracer/hook_tracer /path/to/Anki2/addons21/hook_tracer
```

Restart Anki, preferably with a disposable profile. Open the panel with
**Tools > Hook Tracer**. See the [usage and manual-test guide](docs/usage.md)
and [configuration reference](hook_tracer/config.md).

## Development

Install [uv](https://docs.astral.sh/uv/), then run:

```sh
uv sync --locked
uv run pytest
uv run mypy
uv run ruff check .
uv run ruff format --check .
```

The environment pins Anki/aqt 26.9.3; `uv.lock` records resolved versions.
Use `uv run ruff format .` to format code. The core is Qt-free, and GUI tests
run offscreen; they do not replace a real Anki smoke test. To print real pylib
hook events from a disposable collection, run
`uv run python -m examples.trace_note`.

See [compatibility decisions](docs/compatibility.md), [specification](spec.md),
and [implementation tasks](tasks.md).

## Contribution

Use a branch and PR for each change; update applicable checkboxes in `tasks.md`.
Keep PRs unmerged until reviewed. Run the development checks before submitting.
