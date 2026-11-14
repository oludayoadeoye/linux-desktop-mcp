"""Unit tests for every registered MCP tool; desktop/browser effects are mocked."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import main
from backends.linux import LinuxBackend


@pytest.fixture(autouse=True)
def use_linux_backend_for_existing_linux_tool_tests(monkeypatch):
    # The historical integration tests below mock ydotool/KWin command calls.
    # Force that adapter so the same suite is deterministic on macOS CI too.
    monkeypatch.setattr(main, "desktop_backend", LinuxBackend())


EXPECTED_TOOLS = {
    "desktop_screenshot",
    "mouse_move",
    "mouse_click",
    "keyboard_type",
    "keyboard_hotkey",
    "launch_application",
    "desktop_status",
    "browser_navigate",
    "browser_snapshot",
    "browser_click",
    "browser_type",
    "browser_press_key",
    "window_list",
    "window_focus",
    "window_switch",
    "window_minimize",
    "window_maximize",
    "window_restore",
    "window_close",
}


def test_all_19_tools_are_registered():
    registered = {tool.name for tool in main.mcp._tool_manager.list_tools()}
    assert registered == EXPECTED_TOOLS
    assert len(registered) == 19


def test_desktop_screenshot_returns_png_and_cleans_tempfile(monkeypatch):
    captured = {}

    def fake_run(args, timeout=8.0):
        captured["path"] = Path(args[-1])
        captured["path"].write_bytes(b"fake-png")
        return ""

    monkeypatch.setattr(main, "run_checked", fake_run)
    result = main.desktop_screenshot()
    assert result.data == b"fake-png"
    assert result._format == "png"
    assert not captured["path"].exists()


def test_mouse_move_invokes_ydotool(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "run_checked", lambda args, **kw: calls.append(args) or "")
    assert main.mouse_move(120, 240) == "Mouse moved to (120, 240)."
    assert calls == [["ydotool", "mousemove", "--absolute", "-x", "120", "-y", "240"]]


def test_mouse_click_repeats_requested_button(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "run_checked", lambda args, **kw: calls.append(args) or "")
    assert main.mouse_click("right", 2) == "Performed 2 right click(s)."
    assert calls == [["ydotool", "click", "0xC1"]] * 2


def test_keyboard_type(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "run_checked", lambda args, **kw: calls.append(args) or "")
    assert main.keyboard_type("hello") == "Typed 5 characters."
    assert calls[0][:4] == ["ydotool", "type", "--key-delay", "1"]
    assert calls[0][-1] == "hello"


def test_keyboard_hotkey_normalizes_and_releases_in_reverse(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "run_checked", lambda args, **kw: calls.append(args) or "")
    assert main.keyboard_hotkey(["CTRL", "l"]) == "Pressed ctrl + l."
    assert calls[0] == ["ydotool", "key", "29:1", "38:1", "38:0", "29:0"]


def test_launch_application_uses_allowlist(monkeypatch):
    monkeypatch.setattr(main.shutil, "which", lambda _: "/usr/bin/firefox")
    popen = MagicMock()
    monkeypatch.setattr(main.subprocess, "Popen", popen)
    assert main.launch_application("firefox") == "Launched firefox."
    popen.assert_called_once()
    assert popen.call_args.args[0] == ["/usr/bin/firefox"]


def test_desktop_status_reports_session_and_display(monkeypatch):
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setattr(
        main.shutil,
        "which",
        lambda cmd: "/usr/bin/" + cmd if cmd in {"kscreen-doctor", "ps"} else None,
    )

    def fake_run(args, **kwargs):
        if args[0] == "kscreen-doctor":
            return subprocess.CompletedProcess(args, 0, "Display: HDMI", "")
        return subprocess.CompletedProcess(args, 0, "123 firefox", "")

    monkeypatch.setattr(main.subprocess, "run", fake_run)
    result = main.desktop_status()
    assert "KDE" in result and "wayland" in result
    assert "Display: HDMI" in result and "firefox" in result


def test_browser_navigate_calls_browser_client(monkeypatch):
    calls = []
    monkeypatch.setattr(
        main, "_browser_call", lambda name, args: calls.append((name, args)) or "navigated"
    )
    assert main.browser_navigate("https://example.com") == "navigated"
    assert calls == [("browser_navigate", {"url": "https://example.com"})]


def test_browser_snapshot_calls_browser_client(monkeypatch):
    monkeypatch.setattr(main, "_browser_call", lambda name, args: "snapshot")
    assert main.browser_snapshot() == "snapshot"


def test_browser_click_calls_browser_client(monkeypatch):
    calls = []
    monkeypatch.setattr(
        main, "_browser_call", lambda name, args: calls.append((name, args)) or "clicked"
    )
    assert main.browser_click("Submit") == "clicked"
    assert calls == [("browser_click", {"element": "Submit"})]


def test_browser_type_calls_browser_client(monkeypatch):
    calls = []
    monkeypatch.setattr(
        main, "_browser_call", lambda name, args: calls.append((name, args)) or "typed"
    )
    assert main.browser_type("hello") == "typed"
    assert calls == [("browser_type", {"text": "hello"})]


def test_browser_press_key_calls_browser_client(monkeypatch):
    calls = []
    monkeypatch.setattr(
        main, "_browser_call", lambda name, args: calls.append((name, args)) or "pressed"
    )
    assert main.browser_press_key("Enter") == "pressed"
    assert calls == [("browser_press_key", {"key": "Enter"})]


def test_window_list_serializes_refreshed_windows(monkeypatch):
    rows = [{"caption": "Terminal", "active": True}]
    monkeypatch.setattr(main, "_kwin_refresh", lambda: rows)
    assert json.loads(main.window_list()) == rows


@pytest.mark.parametrize(
    ("tool", "args", "action"),
    [
        (main.window_focus, {"match": "Firefox"}, "focus"),
        (main.window_minimize, {"match": "Firefox"}, "minimize"),
        (main.window_maximize, {"match": "Firefox"}, "maximize"),
        (main.window_restore, {"match": "Firefox"}, "restore"),
        (main.window_close, {"match": "Firefox"}, "close"),
    ],
)
def test_targeted_window_actions(tool, args, action, monkeypatch):
    calls = []
    monkeypatch.setattr(
        main,
        "_kwin_action",
        lambda requested, match: calls.append((requested, match)) or "confirmed",
    )
    assert tool(**args) == "confirmed"
    assert calls == [(action, "Firefox")]


def test_window_switch_next(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "run_checked", lambda args, **kw: calls.append(args) or "")
    assert main.window_switch("next").startswith("Requested next")
    assert calls == [["ydotool", "key", "56:1", "15:1", "15:0", "56:0"]]


def test_window_minimize_active_window(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "run_checked", lambda args, **kw: calls.append(args) or "")
    assert "active window" in main.window_minimize()
    assert calls and calls[0][0] == "ydotool"


def test_window_maximize_active_window(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "run_checked", lambda args, **kw: calls.append(args) or "")
    assert "active window" in main.window_maximize()
    assert calls and calls[0][0] == "ydotool"


def test_window_close_active_window(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "run_checked", lambda args, **kw: calls.append(args) or "")
    assert "Alt+F4" in main.window_close()
    assert calls == [["ydotool", "key", "56:1", "62:1", "62:0", "56:0"]]


def test_browser_navigation_rejects_non_http_urls():
    with pytest.raises(ValueError, match="Only absolute http"):
        main.browser_navigate("file:///etc/passwd")
    with pytest.raises(ValueError, match="Only absolute http"):
        main.browser_navigate("javascript:alert(1)")


def test_run_checked_raises_on_nonzero_exit(monkeypatch):
    monkeypatch.setattr(
        main.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a[0], 1, "", "nope")
    )
    with pytest.raises(RuntimeError, match="nope"):
        main.run_checked(["example-command"])
