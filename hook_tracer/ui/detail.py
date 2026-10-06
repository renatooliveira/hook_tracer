"""Read-only details from serialized events only; no live Anki objects."""

from aqt.qt import QPlainTextEdit

from hook_tracer.core.recorder import TraceEvent


def describe(event: TraceEvent | None, capture_args: bool = True) -> str:
    if event is None:
        return "Select a trace event."
    lines = [f"{event.hook} ({event.kind})", f"Thread: {event.thread}"]
    lines.append(f"Duration: {event.duration_ms:.2f} ms")
    lines.append("Arguments:")
    if not capture_args:
        lines.append("  <argument capture disabled>")
    elif event.args:
        lines.extend(f"  {index}: {arg}" for index, arg in enumerate(event.args))
    else:
        lines.append("  <none>")
    lines.append("Callbacks at fire time:")
    lines.extend(f"  {name} — {owner}" for name, owner in event.callbacks)
    if not event.callbacks:
        lines.append("  <none>")
    if event.kind == "filter":
        fallback = "<dispatch failed>" if event.error else "<not captured>"
        lines.extend(
            (
                f"Filter input: {event.filter_in if event.filter_in is not None else fallback}",
                f"Filter output: {event.filter_out if event.filter_out is not None else fallback}",
                f"Changed: {event.changed if event.changed is not None else 'unknown'}",
            )
        )
    if event.error:
        lines.append(f"Error: {event.error}")
    return "\n".join(lines)


class DetailPane(QPlainTextEdit):
    def __init__(self, capture_args: bool = True) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.capture_args = capture_args
        self.show_event(None)

    def show_event(self, event: TraceEvent | None) -> None:
        self.setPlainText(describe(event, self.capture_args))
