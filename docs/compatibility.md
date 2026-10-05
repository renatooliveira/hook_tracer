# Compatibility decisions

## Initial target

The initial supported target is **Anki 26.9.3 only**, with Python 3.12 and Qt 6.
Both `anki` and `aqt` are pinned to 26.9.3 in the development environment.
This was the latest release available for both packages when phase 0 began.
Do not infer support for earlier or later releases: generated dispatch internals
must be verified before expanding the range. These packages are development
dependencies, not libraries bundled with the add-on.

Package-level tests are not a substitute for the later real-Anki manual checklist.

## Generated dispatch contract

Verified against the installed 26.9.3 `anki/hooks_gen.py` and `aqt/gui_hooks.py`:
class-level `_hooks` lists and class `__call__` dispatch match the specification.
Generated filters thread their first argument through callbacks. Generated
callbacks that raise `Exception` are removed and the same exception is re-raised.
Importantly, upstream does **not** remove callbacks for arbitrary `BaseException`
subclasses; the tracer must preserve that distinction.

Legacy calls run after generated callbacks: `exporters_list_created` delegates to
`runHook("exportersList", ...)`, and GUI `card_will_show` delegates to
`runFilter("prepareQA", ...)`. Legacy dispatch also removes callbacks on
`Exception`. Tests isolate callback lists and restore them afterward.

Import `anki.collection` before `anki.hooks` in standalone probes: importing hooks
first in this release exposes an upstream circular import. Run the initial
contract probes with `uv run python -m unittest discover -s tests -v`.

## GUI discovery without an application

On the development macOS arm64 environment, importing `aqt.gui_hooks` after
`anki.collection` discovers 150 generated instances without creating a
`QApplication`. The subprocess regression probe uses `QT_QPA_PLATFORM=offscreen`
and checks the application is still absent after discovery. Qt libraries must
be installed, but GUI discovery needs no application fixture on this target.
Actual widget/model tests in phase 3 will need a Qt application fixture. Other
platforms still require validation; this is not a cross-platform runtime claim.
