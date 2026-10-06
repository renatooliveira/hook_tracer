"""Atomic, local-only JSON Lines export of an immutable buffer snapshot."""

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .recorder import TraceEvent


def export_jsonl(path: Path, events: Iterable[TraceEvent]) -> None:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temp_path = Path(file.name)
            for event in events:
                file.write(json.dumps(asdict(event), ensure_ascii=True) + "\n")
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
