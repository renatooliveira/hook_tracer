"""Compact, read-only inspector rendered entirely from serialized event data."""

from html import escape

from aqt.qt import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from hook_tracer.core.recorder import TraceEvent


def describe(event: TraceEvent | None, capture_args: bool = True) -> str:
    """Plain-text representation for copying and headless-style assertions."""
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


def render_event(event: TraceEvent | None, capture_args: bool = True) -> str:
    """HTML structure for Qt rich text; escape all user/add-on-controlled reprs."""
    if event is None:
        return "<p>Select a trace event.</p>"

    def section(title: str, rows: list[tuple[str, str]]) -> str:
        cells = "".join(
            f'<tr><td valign="top"><b>{escape(label)}</b></td>'
            f'<td valign="top">{escape(value)}</td></tr>'
            for label, value in rows
        )
        return f"<h4>{escape(title)}</h4><table width='100%' cellspacing='4'>{cells}</table>"

    header = (
        f"<b>{escape(event.hook)}</b> &nbsp; {escape(event.kind)} &nbsp; · &nbsp; "
        f"{event.t_ms:.1f} ms &nbsp; · &nbsp; {event.duration_ms:.2f} ms &nbsp; · &nbsp; "
        f"{escape(event.thread)}"
    )
    if not capture_args:
        args = [("", "Argument capture disabled")]
    elif event.args:
        args = [(f"{index}", arg) for index, arg in enumerate(event.args)]
    else:
        args = [("", "None")]
    callbacks = [
        (str(index + 1), f"{name} — {owner}") for index, (name, owner) in enumerate(event.callbacks)
    ]
    if not callbacks:
        callbacks = [("", "No callbacks registered")]
    parts = [
        f"<p>{header}</p>",
        section("Arguments", args),
        section("Callbacks at fire time", callbacks),
    ]
    if event.kind == "filter":
        fallback = "Dispatch failed" if event.error else "Not captured"
        parts.append(
            section(
                "Filter",
                [
                    ("Input", event.filter_in if event.filter_in is not None else fallback),
                    ("Output", event.filter_out if event.filter_out is not None else fallback),
                    ("Changed", str(event.changed) if event.changed is not None else "Unknown"),
                ],
            )
        )
    if event.error:
        parts.append(section("Error", [("", event.error)]))
    return "".join(parts)


class DetailPane(QWidget):
    def __init__(self, capture_args: bool = True) -> None:
        super().__init__()
        self.capture_args = capture_args
        self._text = describe(None)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        header = QHBoxLayout()
        header.addWidget(QLabel("Event details", self))
        header.addStretch()
        self.copy_button = QPushButton("Copy details", self)
        self.copy_button.clicked.connect(self.copy_details)
        header.addWidget(self.copy_button)
        layout.addLayout(header)
        self.body = QTextBrowser(self)
        self.body.setReadOnly(True)
        self.body.setOpenExternalLinks(False)
        layout.addWidget(self.body)
        self.show_event(None)

    def show_event(self, event: TraceEvent | None) -> None:
        self._text = describe(event, self.capture_args)
        self.body.setHtml(render_event(event, self.capture_args))
        self.copy_button.setEnabled(event is not None)

    def copy_details(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._text)

    def toPlainText(self) -> str:
        return self.body.toPlainText()
