"""Validate Anki's add-on config without depending on its GUI."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Config:
    trace_on_startup: bool = False
    buffer_size: int = 5000
    capture_args: bool = True
    repr_max_len: int = 200
    muted_hooks: tuple[str, ...] = ()
    trace_legacy: bool = False  # reserved; never enabled in v1


def validate(raw: object) -> tuple[Config, tuple[str, ...]]:
    """Use safe defaults for invalid keys; never block add-on startup."""
    defaults = Config()
    if not isinstance(raw, dict):
        return defaults, ("config must be an object; using defaults",)
    values: dict[str, Any] = {}
    warnings: list[str] = []
    for key in ("trace_on_startup", "capture_args"):
        value = raw.get(key, getattr(defaults, key))
        if type(value) is bool:
            values[key] = value
        else:
            warnings.append(f"{key} must be a boolean; using default")
    for key, maximum in (("buffer_size", 100_000), ("repr_max_len", 10_000)):
        value = raw.get(key, getattr(defaults, key))
        if type(value) is int and 1 <= value <= maximum:
            values[key] = value
        else:
            warnings.append(f"{key} must be an integer from 1 to {maximum}; using default")
    muted = raw.get("muted_hooks", [])
    if (
        isinstance(muted, list)
        and len(muted) <= 1000
        and all(type(name) is str and bool(name) for name in muted)
    ):
        values["muted_hooks"] = tuple(dict.fromkeys(muted))
    else:
        warnings.append("muted_hooks must be a list of at most 1000 nonempty names; using default")
    legacy = raw.get("trace_legacy", False)
    if type(legacy) is not bool:
        warnings.append("trace_legacy must be a boolean; leaving legacy tracing disabled")
    elif legacy:
        warnings.append("trace_legacy=true is unsupported in v1; legacy tracing stays disabled")
    return Config(**values), tuple(warnings)
