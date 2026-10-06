# Usage and manual validation

## Panel and debug console

**Tools > Hook Tracer** opens the dock. Use **Start recording** / **Stop
recording** in the panel to control capture; recording starts off unless
`trace_on_startup` is enabled in the [configuration](../hook_tracer/config.md).
Closing the panel does not stop recording.

The stream has Clear, substring/regex hook-name filtering, and a no-callbacks
filter. Invalid regexes show an error without interrupting capture. The
**View: Stream / Catalog** buttons switch views below the dock header. Select a
row for the compact detail inspector (arguments, callback owners, filter
input/output and errors); **Copy details** copies stored text, never live
objects. The Catalog view shows discovered hooks, current registrations,
owners and session fire counts, sorted by callback count. Counts include
attempted dispatches, even those that raise, only while recording and
unmuted. Clearing the buffer does not reset counts. The catalog refreshes
every second while open.

A stream-row **Mute recording for selected hook** action stops new events for
that hook from entering the buffer or debug console; **Session mutes** allows
unmuting even if no rows remain. Mutes take effect immediately but are
session-only until **Save mutes as default** is clicked. Filtering is display-
only: it does not prevent eviction or console spam. The panel also displays
recording errors. **Export JSON Lines…** saves the entire current buffer,
including hidden rows, after a privacy confirmation.

Anki's debug console (Ctrl+:) displays retained events and updates every
250 ms while open; closing it stops console output but not recording. To
unpatch during a session, run `import hook_tracer; hook_tracer.stop()` there.
Restart Anki or run `hook_tracer.start(aqt.mw)` to re-enable it.

## Limitations and privacy

Only **Anki 26.9.3** is supported. Anki loads add-ons by sorted directory name
after creating its main window, so earlier hooks and hooks fired by earlier
add-ons cannot be captured. Changing the add-on folder name to load first is
not a supported cross-version guarantee. Generated legacy delegation runs
normally, but legacy-only hooks, Rust backend calls and JavaScript execution
are not separately traced.

Recording is local and bounded, with no network transmission by Hook Tracer.
Captured argument reprs, the debug-console log, copied details and JSON Lines
exports may contain private card/note or add-on content. Review exports before
sharing them. Arguments are serialized at fire time; the UI does not retain or
expand live Anki objects.

## Manual smoke test (outstanding)

Use a disposable profile on Anki 26.9.3:

1. Open the panel, start recording, review 100 cards, open the editor and
   browser, and run a sync. Confirm reviewer events such as
   `gui.reviewer_did_answer_card` and no change in Anki behavior or errors in
   the debug console. Check responsiveness and bounded stream rows.
2. Exercise start/stop, clear, name/no-callback filters, invalid regex, detail
   selection, the catalog, current callback owners, and dynamic registration
   and removal of an add-on callback.
3. During a media download, verify that temporarily muting
   `gui.media_sync_did_progress` prevents console flooding. Save/unmute mutes
   and restart to check persistence.
4. Test JSON Lines export and cancel. Confirm export contains the full buffer
   rather than just filtered rows, and inspect it before sharing.
5. Close/reopen the panel and stop/unpatch the tracer. Confirm timers stop,
   reviewer behavior remains unchanged, and the debug console has no errors.

For a sampled frequency count (up to 5000 retained events by default), run:

```python
from collections import Counter
import hook_tracer

Counter(e.hook for e in hook_tracer.start(aqt.mw).recorder.snapshot()).most_common(20)
```

This is **not** a full-session count after eviction. The real-Anki smoke test,
100-card responsiveness check and noisy-hook measurement remain outstanding;
automated offscreen Qt and real pylib `Collection` tests are not substitutes.
