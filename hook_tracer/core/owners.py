"""Resolve callbacks to stable, Qt-free display metadata."""

import functools
import inspect
from collections.abc import Callable, Mapping


def callback_owner(callback: object, add_on_names: Mapping[str, str]) -> tuple[str, str]:
    """Return (qualified callback name, owner); never retain the callback."""
    try:
        seen: set[int] = set()
        obj = callback
        while id(obj) not in seen:
            seen.add(id(obj))
            if isinstance(obj, functools.partial):
                obj = obj.func
            elif inspect.ismethod(obj):
                obj = obj.__func__
            else:
                wrapped = getattr(obj, "__wrapped__", None)
                if wrapped is None:
                    break
                obj = wrapped
        module = getattr(obj, "__module__", None)
        qualname = getattr(obj, "__qualname__", None)
        if not isinstance(module, str) or not isinstance(qualname, str):
            target = type(obj).__call__ if callable(obj) else type(obj)
            module = getattr(target, "__module__", None)
            qualname = getattr(target, "__qualname__", None)
        if not isinstance(module, str) or not isinstance(qualname, str):
            return "<callback unknown>", "unknown"
        folder = module.split(".", 1)[0]
        if folder in {"anki", "aqt"}:
            owner = "core"
        elif folder in add_on_names:
            display = add_on_names[folder]
            owner = f"{display} ({folder})" if display != folder else folder
        else:
            owner = "unknown"
        return f"{module}.{qualname}", owner
    except Exception:
        return "<callback unknown>", "unknown"


def add_on_names(folders: list[str], display_name: Callable[[str], str]) -> dict[str, str]:
    """Snapshot installed add-ons on the main thread before background dispatch."""
    names: dict[str, str] = {}
    for folder in folders:
        try:
            name = display_name(folder)
            names[folder] = name if isinstance(name, str) and name else folder
        except Exception:
            names[folder] = folder
    return names
