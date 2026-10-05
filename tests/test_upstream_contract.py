"""Compatibility probes; import Collection first to avoid upstream import cycles."""

import inspect
import unittest
from unittest.mock import patch

import anki.collection  # noqa: F401
import anki.hooks


class UpstreamContractTests(unittest.TestCase):
    def test_generated_layout(self):
        hooks = [
            obj
            for obj in vars(anki.hooks).values()
            if type(obj).__name__.startswith("_")
            and type(obj).__name__.endswith(("Hook", "Filter"))
        ]
        self.assertTrue(hooks)
        for hook in hooks:
            self.assertIsInstance(vars(type(hook))["_hooks"], list)
            for method in ("append", "remove", "count", "__call__"):
                self.assertTrue(callable(getattr(hook, method)))

    def test_hook_failure_removes_callback_and_preserves_exception(self):
        hook = anki.hooks.exporters_list_created
        error = ValueError("probe")

        def failing(exporters):
            raise error

        with patch.object(type(hook), "_hooks", []):
            hook.append(failing)
            with self.assertRaises(ValueError) as raised:
                hook([])
            self.assertIs(raised.exception, error)
            self.assertEqual(hook.count(), 0)

    def test_legacy_delegation_follows_generated_callbacks(self):
        hook = anki.hooks.exporters_list_created
        calls = []
        with (
            patch.object(type(hook), "_hooks", [lambda value: calls.append("new")]),
            patch.object(
                anki.hooks, "_hooks", {"exportersList": [lambda value: calls.append("legacy")]}
            ),
        ):
            hook([])
        self.assertEqual(calls, ["new", "legacy"])

    def test_generated_filters_thread_the_first_argument(self):
        hook = next(
            obj for obj in vars(anki.hooks).values() if type(obj).__name__.endswith("Filter")
        )
        with patch.object(type(hook), "_hooks", []):
            hook.append(lambda value, *args: value + "a")
            hook.append(lambda value, *args: value + "b")
            extra = len(inspect.signature(hook).parameters) - 1
            self.assertEqual(hook("", *([None] * extra)), "ab")


if __name__ == "__main__":
    unittest.main()
