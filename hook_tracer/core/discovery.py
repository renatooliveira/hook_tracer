"""Find generated hook instances without importing Anki or Qt."""

from dataclasses import dataclass
from types import ModuleType
from typing import Literal

Kind = Literal["hook", "filter"]


@dataclass(frozen=True)
class HookInfo:
    name: str
    kind: Kind
    instance: object


def discover(modules: list[tuple[str, ModuleType]]) -> list[HookInfo]:
    """Discover (prefix, module) pairs; the first export of a class wins."""
    found: list[HookInfo] = []
    seen: set[type] = set()
    for prefix, module in modules:
        for name, obj in vars(module).items():
            cls = type(obj)
            if cls in seen or not cls.__name__.startswith("_"):
                continue
            if cls.__name__.endswith("Hook"):
                kind: Kind = "hook"
            elif cls.__name__.endswith("Filter"):
                kind = "filter"
            else:
                continue
            if not isinstance(getattr(obj, "_hooks", None), list):
                continue
            if not all(
                callable(getattr(obj, method, None)) for method in ("append", "remove", "count")
            ):
                continue
            found.append(HookInfo(f"{prefix}.{name}", kind, obj))
            seen.add(cls)
    return found
