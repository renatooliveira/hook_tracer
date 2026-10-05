# Compatibility decisions

## Initial target

The initial supported target is **Anki 26.9.3 only**, with Python 3.12 and Qt 6.
Both `anki` and `aqt` are pinned to 26.9.3 in the development environment.
This was the latest release available for both packages when phase 0 began.
Do not infer support for earlier or later releases: generated dispatch internals
must be verified before expanding the range. These packages are development
 dependencies, not libraries bundled with the add-on.

Package-level tests are not a substitute for the later real-Anki manual checklist.
