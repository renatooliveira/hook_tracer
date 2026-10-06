"""Minimal copies of generated Anki dispatch, including legacy delegation."""

legacy_calls: list[object] = []


class _DidSomethingHook:
    _hooks: list[object] = []

    def append(self, callback):
        self._hooks.append(callback)

    def remove(self, callback):
        if callback in self._hooks:
            self._hooks.remove(callback)

    def count(self):
        return len(self._hooks)

    def __call__(self, value=None):
        for hook in self._hooks:
            try:
                hook(value)
            except Exception:
                self._hooks.remove(hook)
                raise
        legacy_calls.append(value)


class _TransformFilter:
    _hooks: list[object] = []

    def append(self, callback):
        self._hooks.append(callback)

    def remove(self, callback):
        if callback in self._hooks:
            self._hooks.remove(callback)

    def count(self):
        return len(self._hooks)

    def __call__(self, value, suffix=""):
        for filter in self._hooks:
            try:
                value = filter(value, suffix)
            except Exception:
                self._hooks.remove(filter)
                raise
        return value


did_something = _DidSomethingHook()
transform = _TransformFilter()
alias = did_something
unrelated = object()
