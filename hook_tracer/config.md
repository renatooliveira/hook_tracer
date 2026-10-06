# Hook Tracer settings

Edit through Anki's **Tools > Add-ons > Hook Tracer > Config**. Restart Anki (or stop and start the tracer) to apply these settings; the panel's **Save mutes as default** button is the exception: it updates `muted_hooks` immediately and persists it for next launch. Merely muting or unmuting in the panel is session-only. Editing the config dialog while the tracer is running does not reconfigure the running recorder.

| Key | Default | Valid values | Meaning |
| --- | --- | --- | --- |
| `trace_on_startup` | `false` | boolean | Start recording when the add-on loads. Earlier Anki/add-on hooks cannot be captured. |
| `buffer_size` | `5000` | integer 1–100000 | Maximum number of events in memory; oldest are evicted. |
| `capture_args` | `true` | boolean | Store bounded string summaries of arguments and filter values. |
| `repr_max_len` | `200` | integer 1–10000 | Maximum characters per captured value's repr. |
| `muted_hooks` | `[]` | list of up to 1000 nonempty hook names, e.g. `["gui.media_sync_did_progress"]` | Do not record these hooks; Anki still calls their callbacks. |
| `trace_legacy` | `false` | boolean | Reserved for optional future legacy tracing. **`true` is unsupported in v1 and is ignored**, with a warning in the panel and Anki's console output. |

Invalid settings fall back individually to defaults and produce warnings. Counts include eligible fires while recording and unmuted, independent of buffer clearing. No data is sent off-machine. **Argument reprs and JSON Lines exports may contain note, card, or add-on content**; share exports only after reviewing them. The export confirmation is shown before choosing a destination. Session mutes take effect immediately; use **Save mutes as default** to keep the current set across restarts.
