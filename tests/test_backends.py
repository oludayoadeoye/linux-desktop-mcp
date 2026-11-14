"""Cross-platform desktop backend tests that do not require a real desktop."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backends.macos import MacOSBackend


def fake_quartz():
    return SimpleNamespace(
        CGEventCreateKeyboardEvent=MagicMock(side_effect=["down", "up"]),
        CGEventSetFlags=MagicMock(),
        CGEventPost=MagicMock(),
        kCGHIDEventTap=7,
    )


def test_macos_hotkey_emits_command_l_events():
    backend = MacOSBackend.__new__(MacOSBackend)
    backend.q = fake_quartz()

    result = backend.keyboard_hotkey(["command", "l"])

    assert result == "Pressed command + l."
    assert backend.q.CGEventCreateKeyboardEvent.call_args_list[0].args == (None, 37, True)
    assert backend.q.CGEventCreateKeyboardEvent.call_args_list[1].args == (None, 37, False)
    assert backend.q.CGEventSetFlags.call_args_list[0].args == ("down", 1 << 20)
    assert backend.q.CGEventPost.call_count == 2


def test_macos_hotkey_rejects_unknown_key():
    backend = MacOSBackend.__new__(MacOSBackend)
    backend.q = fake_quartz()

    with pytest.raises(ValueError, match="Unsupported key"):
        backend.keyboard_hotkey(["command", "not-a-key"])


def test_macos_hotkey_requires_one_non_modifier():
    backend = MacOSBackend.__new__(MacOSBackend)
    backend.q = fake_quartz()

    with pytest.raises(ValueError, match="one non-modifier"):
        backend.keyboard_hotkey(["command", "shift"])


def test_macos_window_matching_prefers_exact_application():
    rows = [
        {"resourceClass": "Safari", "caption": "Developer docs"},
        {"resourceClass": "Terminal", "caption": "Safari build log"},
    ]

    result = MacOSBackend._match(rows, "Safari")

    assert result is rows[0]


def test_macos_window_matching_falls_back_to_title():
    rows = [{"resourceClass": "Terminal", "caption": "Safari build log"}]

    assert MacOSBackend._match(rows, "build") is rows[0]


def test_macos_app_allowlist_contains_native_apps():
    assert MacOSBackend.APP_ALLOWLIST["finder"] == "Finder"
    assert MacOSBackend.APP_ALLOWLIST["terminal"] == "Terminal"
    assert MacOSBackend.APP_ALLOWLIST["safari"] == "Safari"
