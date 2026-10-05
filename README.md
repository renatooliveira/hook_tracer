# Hook Tracer

A developer add-on for observing Anki's Python hooks and filters. **Scaffold only:**
recording and the panel are not implemented yet. See [spec.md](spec.md) and
[tasks.md](tasks.md) for the design and phased implementation plan.

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

See [compatibility decisions](docs/compatibility.md) for verified upstream
behavior, import-order requirements, and platform limitations. Future real-Anki
smoke tests should use a disposable profile; installation and manual-test
instructions will be added with the runnable add-on lifecycle.

## Layout

- `hook_tracer/__init__.py`: future add-on lifecycle entry point
- `hook_tracer/core/`: pure-Python recording, discovery, patching, and ownership
- `hook_tracer/ui/`: future main-thread Qt interface
- `tests/`: upstream compatibility probes and headless tests

## Contribution workflow

Use one branch and PR per phase, and one commit per checklist item. Update the
corresponding checkbox in the same commit. Keep PRs unmerged until reviewed.
