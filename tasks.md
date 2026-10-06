# Hook Tracer Tasks

Source: `spec.md`. Tasks are ordered by dependency and grouped by its milestones. Unchecked items are not yet implemented. Milestones 1–5 define v1; milestone 6 is optional.

## 0. Resolve prerequisites and scaffold

- [x] Choose the supported Anki version range and pin `anki`/`aqt` to the initial target version.
- [x] Verify generated hook/filter class layout on supported versions, including exception removal and legacy dispatch behavior.
- [x] Determine whether GUI-hook discovery tests require a `QApplication` fixture.
- [x] Scaffold `hook_tracer/core/`, `hook_tracer/ui/`, `tests/`, and the add-on manifest.
- [x] Set up `uv` or a venv, `pytest`, `mypy`, and `ruff`; document development and check commands.
- [x] Resolve the legacy-tracing scope discrepancy: explicit legacy tracing is milestone 6 stretch; `trace_legacy` stays disabled in v1 (see scope decision in `spec.md`).

## 1. Headless core

### Discovery — `hook_tracer/core/discovery.py`

- [x] Discover generated instances in supplied modules using `append`, `remove`, `count`, `_hooks`, and the class-name convention.
- [x] Classify hooks versus filters and assign stable names with `gui` or `anki` prefixes.
- [x] Deduplicate by class across modules and re-exports.
- [x] Test valid hooks/filters, unrelated objects, and duplicate exports without Qt imports.

### Recorder — `hook_tracer/core/recorder.py`

- [x] Define the frozen `TraceEvent` with all specified fields: sequence, elapsed time, hook, kind, thread, duration, callbacks, args, filter input/output, changed flag, and error.
- [x] Implement bounded `deque(maxlen=buffer_size)` storage, monotonically increasing sequence IDs, incremental reads, snapshots, and clear.
- [x] Make sequence allocation and buffer reads/writes safe under concurrent recording; keep Qt out of the core.
- [x] Implement bounded `reprlib.Repr` summaries, one-line display data, and `capture_args` support.
- [x] Capture filter input before dispatch and output after dispatch; implement the specified identity-and-inequality changed rule safely.
- [x] Store only serialized metadata, never live arguments, callbacks, results, exceptions, or tracebacks.
- [x] Add a recording-error counter and protect against failing reprs, comparisons, and serialization.
- [x] Test eviction, sequence ordering, clear/incremental-read behavior, truncation, disabled argument capture, filter results, and lack of object retention.

### Patching — `hook_tracer/core/patching.py`

- [x] Install class-level `__call__` wrappers and retain exact originals in an idempotent registry.
- [x] Add recording state, muted-hook checks, and the cheap paused path directly to the original dispatch.
- [x] Snapshot callbacks before dispatch and measure total dispatch duration with `perf_counter_ns`.
- [x] Preserve return values, callback ordering, filter chaining, removal-on-error, and original exceptions unchanged.
- [x] Isolate all tracer bookkeeping failures so they cannot prevent dispatch or replace its exception; increment the error counter when recording fails.
- [x] Add a thread-local re-entrancy guard for recorder activity and expose a guard for tracer-owned UI activity.
- [x] Restore exact original callables on uninstall; test repeated install/uninstall.

### Headless verification — `tests/`

- [x] Build `fake_hooks.py` matching generated hook/filter dispatch, callback removal, and legacy delegation.
- [x] Test every fire, callback snapshots, filters, muted/paused recording, nesting, and guard cleanup after failure.
- [x] Inject recorder failures and assert original results and exceptions remain unchanged.
- [x] Fire hooks from multiple threads and verify event counts, unique sequence IDs, and thread names.
- [x] Add real `anki.hooks` integration tests with a temporary `Collection` and an action such as adding a note; always clean up patches and collections.
- [x] Add a runnable headless script that prints a trace of adding a note.
- [x] Add a `timeit` comparison of unpatched versus paused-patched dispatch with a loose, non-flaky threshold.

**Exit check:** headless tests pass, the example prints real pylib events, and core modules import without Qt.

## 2. Console trace in Anki

- [x] Implement `hook_tracer/__init__.py` lifecycle: discover both modules, install patches, and cleanly stop/unpatch.
- [x] Add a Tools-menu recording toggle and temporary debug-console event output.
- [x] Load startup-recording configuration early enough to capture subsequent startup hooks; default to paused.
- [x] Resolve add-on load-order expectations and document any startup coverage limitations.
- [x] Document symlinking `hook_tracer/` into Anki's shared `addons21` directory.
- [ ] Manually review cards and verify expected reviewer hook names appear without changing behavior.
- [ ] Measure noisy hooks using session fire counts before proposing default mutes.

**Exit check:** reviewing a card prints expected hook events; toggling recording and stopping the tracer work safely.

## 3. Stream panel

- [x] Add **Tools > Hook Tracer** and a reusable `QDockWidget` in `ui/dock.py`.
- [x] Implement `ui/stream_model.py` with Time, Hook, Kind, Thread, Duration, Callbacks, and Args columns.
- [x] Refresh on a main-thread `QTimer` every 250 ms, reading events newer than the last sequence and using `beginInsertRows`.
- [x] Handle buffer eviction, missed refreshes, clear, and reopening without duplicate rows or unbounded model memory.
- [x] Highlight off-main-thread events; never touch widgets from dispatch threads.
- [x] Add pause/resume, clear, substring/regex name filtering, and “hide hooks with no callbacks.”
- [x] Add a quick **Mute recording for this hook** action from a stream row (including `gui.media_sync_did_progress` during media downloads), with visible session-muted state and an easy unmute path. Hiding from view alone must not be presented as protection against buffer eviction or console spam.
- [x] Handle invalid regex input without disrupting recording or the UI.
- [x] Guard tracer-owned UI work against recursive tracing and stop timers on teardown.
- [x] Test model updates/filtering with Qt fixtures where feasible.
- [ ] Run a 100-card review session and verify responsiveness and bounded row retention.

**Exit check:** the live panel stays responsive during the review session, with working controls and thread highlighting.

## 4. Detail, owners, and catalog

### Callback ownership — `core/owners.py`

- [x] Unwrap bound methods and `functools.partial` callbacks, including nested wrappers.
- [x] Resolve qualified callback names and add-on folders from `__module__`; label `aqt`/`anki` callbacks as core.
- [x] Map folders to display names through an injected add-on-manager adapter, keeping the core Qt-free.
- [x] Handle unknown modules and unusual callable objects safely; test ownership resolution headlessly.
- [x] Store callback names and owners at fire time so subsequent registration changes do not alter old events.

### Details — `ui/detail.py`

- [x] Show selected-event argument reprs, callback names/owners, filter input/output and changed flag, and exception summary.
- [x] Show stored reprs in full within the configured capture limit; do not retain original objects for expansion.
- [x] Handle empty selection, cleared/evicted events, disabled argument capture, and failed filter dispatch.

### Catalog — `ui/catalog.py`

- [x] List every discovered hook with kind, session fire count, current callback count, and owning add-ons.
- [x] Maintain session counts independently of buffer eviction; define count behavior for pause, mute, and clear.
- [x] Refresh current registrations safely and support sorting by callback count.
- [ ] Verify attribution and dynamic callback registration/removal in a real Anki session.

**Exit check:** details explain each recorded dispatch and the catalog shows current listeners with usable ownership labels.

## 5. Polish and v1 validation

- [ ] Ship `config.json` defaults and `config.md` documentation for `trace_on_startup`, `buffer_size`, `capture_args`, `repr_max_len`, `muted_hooks`, and `trace_legacy`.
- [ ] Validate config types/ranges and document when changes take effect through Anki's add-on config dialog; explain that `trace_legacy=true` is unsupported and keep legacy tracing disabled in v1.
- [ ] Add selected-hook mute/unmute controls and persist changes back to config when the user opts to keep a session mute across restarts; distinguish temporary session mutes from persisted mutes.
- [ ] Display the internal recording-error counter in the panel.
- [ ] Export a snapshot of the current buffer as JSON Lines, not just visible filtered rows.
- [ ] Warn before export that arguments may contain card/note content; handle cancel and write failures safely.
- [ ] Test JSON serialization, config validation, mute persistence, and export behavior.
- [ ] Verify clean shutdown/unpatch, timer cleanup, bounded memory, and local-only operation.
- [ ] Run `pytest`, `mypy`, and `ruff`; repeat the paused-overhead check.
- [ ] Complete the real-Anki checklist: open panel, review cards, open editor/browser, sync, exercise controls/details/catalog/export, and check the debug console for errors.
- [ ] Document installation, supported versions, usage, privacy considerations, known limitations, and the manual test checklist.

**Exit check:** v1 requirements are covered by automated checks and a recorded manual smoke test on the supported Anki target.

## 6. Optional stretch work — not required for v1

- [ ] Decide whether per-callback timing is worth replacing the original dispatch loop; document semantic-drift risks before implementing.
- [ ] If approved, implement per-callback timing with parity tests for ordering, filter chaining, callback removal, exceptions, and legacy behavior.
- [ ] Implement optional `runHook`/`runFilter` tracing behind `trace_legacy`, including install/uninstall and nested generated-to-legacy dispatch tests.
- [ ] Add a “record this action” control that captures only between two clicks.

## Post-v1 backlog — broader Anki activity tracing (not hooks)

These are optional, separately labeled **boundary events**, not hook/filter events. Validate the use case before expanding Hook Tracer's scope; keep each category opt-in, bounded, safe to unpatch, and off by default.

- [ ] Evaluate Python → Rust command tracing at `RustBackend._run_command`: measure call volume/overhead, preserve exceptions and results, and resolve readable operation names reliably (caller-frame inference needs validation). Avoid logging protobuf payloads by default.
- [ ] Evaluate SQL tracing at `DBProxy._query`: report timings and sanitized query templates, not values or results by default; account for the same operation also appearing as a backend call and protect card/note content.
- [ ] Evaluate JS → Python bridge events at `AnkiWebView._onBridgeCmd`: identify what is *not* already exposed by `gui.webview_did_receive_js_message` (including `domDone`/`close`), and avoid duplicate events.
- [ ] Evaluate Python → JS events at `AnkiWebView.evalWithCallback` (including `eval` delegation): distinguish enqueue time from actual asynchronous execution/completion, avoid double-counting, and redact JS payloads and callback results.
- [ ] If there is demonstrated demand, design category filters, correlation with hook events, privacy defaults, overhead limits, compatibility tests, and a clear product name/scope before implementation.

## Deferred product decisions

- [ ] Choose internal-team distribution, public AnkiWeb distribution, or integration into Anki's debug console. Public distribution remains outside v1.
- [ ] Revisit default muted hooks using measured data rather than assumptions. `gui.media_sync_did_progress` was reported flooding the phase-2 debug console during a large media download; measure frequency and buffer/console impact before proposing a default mute, and keep it discoverable when muted.
