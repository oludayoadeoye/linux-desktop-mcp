from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Annotated

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.fastmcp import FastMCP, Image
from pydantic import Field

mcp = FastMCP(
    "EndeavourOS Desktop Control",
    instructions=(
        "Control the user's local KDE Plasma desktop on Wayland. "
        "Use screenshots to inspect the screen before acting. "
        "Never claim an action succeeded unless its command succeeded."
    ),
    host="127.0.0.1",
    port=8932,
)

APP_ALLOWLIST = {
    "firefox": "firefox",
    "brave": "brave",
    "dolphin": "dolphin",
    "konsole": "konsole",
    "kate": "kate",
    "spectacle": "spectacle",
    "systemsettings": "systemsettings",
}
KEY_CODES = {
    "escape": 1,
    "1": 2,
    "2": 3,
    "3": 4,
    "4": 5,
    "5": 6,
    "6": 7,
    "7": 8,
    "8": 9,
    "9": 10,
    "0": 11,
    "minus": 12,
    "equal": 13,
    "backspace": 14,
    "tab": 15,
    "q": 16,
    "w": 17,
    "e": 18,
    "r": 19,
    "t": 20,
    "y": 21,
    "u": 22,
    "i": 23,
    "o": 24,
    "p": 25,
    "enter": 28,
    "ctrl": 29,
    "a": 30,
    "s": 31,
    "d": 32,
    "f": 33,
    "g": 34,
    "h": 35,
    "j": 36,
    "k": 37,
    "l": 38,
    "shift": 42,
    "z": 44,
    "x": 45,
    "c": 46,
    "v": 47,
    "b": 48,
    "n": 49,
    "m": 50,
    "space": 57,
    "alt": 56,
    "home": 102,
    "up": 103,
    "pageup": 104,
    "left": 105,
    "right": 106,
    "end": 107,
    "down": 108,
    "pagedown": 109,
    "delete": 111,
    "super": 125,
    "f11": 87,
    "f12": 88,
}
BUTTONS = {"left": "0xC0", "right": "0xC1", "middle": "0xC2"}


def run_checked(args: list[str], timeout: float = 8.0) -> str:
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip() or "Command failed"
        raise RuntimeError(f"{args[0]} failed ({result.returncode}): {message}")
    return result.stdout.strip()


@mcp.tool()
def desktop_screenshot() -> Image:
    """Capture the current desktop using KDE Spectacle and return the image."""
    fd, filename = tempfile.mkstemp(prefix="desktop-control-", suffix=".png")
    os.close(fd)
    path = Path(filename)
    try:
        run_checked(["spectacle", "-b", "-n", "-o", str(path)], timeout=20)
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError("Spectacle did not produce a screenshot")
        return Image(data=path.read_bytes(), format="png")
    finally:
        path.unlink(missing_ok=True)


@mcp.tool()
def mouse_move(
    x: Annotated[int, Field(ge=0, le=20000)],
    y: Annotated[int, Field(ge=0, le=20000)],
) -> str:
    """Move the mouse pointer to absolute desktop coordinates."""
    run_checked(["ydotool", "mousemove", "--absolute", "-x", str(x), "-y", str(y)])
    return f"Mouse moved to ({x}, {y})."


@mcp.tool()
def mouse_click(
    button: Annotated[str, Field(pattern="^(left|right|middle)$")] = "left",
    clicks: Annotated[int, Field(ge=1, le=2)] = 1,
) -> str:
    """Click at the current pointer position; supports left, right, or middle."""
    for _ in range(clicks):
        run_checked(["ydotool", "click", BUTTONS[button]])
    return f"Performed {clicks} {button} click(s)."


@mcp.tool()
def keyboard_type(text: Annotated[str, Field(min_length=1, max_length=4000)]) -> str:
    """Type literal text into the currently focused application."""
    run_checked(["ydotool", "type", "--key-delay", "1", text], timeout=30)
    return f"Typed {len(text)} characters."


@mcp.tool()
def keyboard_hotkey(keys: list[str]) -> str:
    """Press a key or key combination, e.g. ['ctrl', 'l'] or ['enter']."""
    if not keys or len(keys) > 4:
        raise ValueError("Provide between 1 and 4 keys.")
    normalized = [key.lower() for key in keys]
    unknown = [key for key in normalized if key not in KEY_CODES]
    if unknown:
        raise ValueError(f"Unsupported key name(s): {', '.join(unknown)}")
    events = [f"{KEY_CODES[key]}:1" for key in normalized]
    events += [f"{KEY_CODES[key]}:0" for key in reversed(normalized)]
    run_checked(["ydotool", "key", *events])
    return f"Pressed {' + '.join(normalized)}."


@mcp.tool()
def launch_application(
    application: Annotated[
        str, Field(pattern="^(firefox|brave|dolphin|konsole|kate|spectacle|systemsettings)$")
    ],
) -> str:
    """Launch an allowlisted desktop application."""
    executable = APP_ALLOWLIST[application]
    resolved = shutil.which(executable)
    if not resolved:
        raise RuntimeError(f"{executable} is not installed or not on PATH.")
    subprocess.Popen(
        [resolved],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return f"Launched {application}."


@mcp.tool()
def desktop_status() -> str:
    """Report desktop session, display configuration, and selected running apps."""
    session = {
        key: os.environ.get(key, "")
        for key in ("XDG_CURRENT_DESKTOP", "XDG_SESSION_TYPE", "WAYLAND_DISPLAY")
    }
    display = ""
    if shutil.which("kscreen-doctor"):
        try:
            display = run_checked(["kscreen-doctor", "-o"], timeout=5)
        except Exception as exc:
            display = f"Display query unavailable: {exc}"
    apps = ""
    if shutil.which("ps"):
        result = subprocess.run(
            ["ps", "-eo", "pid=,comm=,args="],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        selected = [
            line.strip()
            for line in result.stdout.splitlines()
            if any(name in line.lower() for name in APP_ALLOWLIST)
        ][:30]
        apps = "\n".join(selected)
    return (
        f"Session: {session}\n\nDisplays:\n{display or 'Unavailable'}"
        f"\n\nSelected running applications:\n{apps or 'None detected'}"
    )


# Browser integration: one persistent client session keeps the Playwright context alive.
_browser_loop = None
_browser_thread = None
_browser_ready = None
_browser_session = None
_browser_transport = None
_browser_transport_cm = None
_browser_session_cm = None


async def _browser_initialize():
    global _browser_transport, _browser_transport_cm, _browser_session, _browser_session_cm
    _browser_transport_cm = streamablehttp_client("http://127.0.0.1:8931/mcp")
    read, write, _ = await _browser_transport_cm.__aenter__()
    _browser_session_cm = ClientSession(read, write)
    _browser_session = await _browser_session_cm.__aenter__()
    await _browser_session.initialize()


def _browser_start():
    global _browser_loop, _browser_thread, _browser_ready
    if _browser_loop is not None:
        return
    _browser_ready = concurrent.futures.Future()

    def runner():
        global _browser_loop
        loop = asyncio.new_event_loop()
        _browser_loop = loop
        asyncio.set_event_loop(loop)

        async def init():
            await _browser_initialize()

        try:
            _browser_ready.set_result(loop.run_until_complete(init()))
        except Exception as exc:
            _browser_ready.set_exception(exc)
            return
        loop.run_forever()

    _browser_thread = threading.Thread(target=runner, name="playwright-mcp-client", daemon=True)
    _browser_thread.start()
    _browser_ready.result(timeout=25)


def _browser_call(tool_name: str, arguments: dict) -> str:
    _browser_start()

    async def invoke():
        result = await _browser_session.call_tool(tool_name, arguments)
        parts = []
        for item in result.content:
            if getattr(item, "text", None):
                parts.append(item.text)
            elif getattr(item, "type", None) == "image":
                parts.append("[Screenshot image returned by browser tool]")
        if result.isError:
            raise RuntimeError("\n".join(parts) or "Browser MCP call failed")
        return "\n".join(parts) or "Browser action completed."

    future = asyncio.run_coroutine_threadsafe(invoke(), _browser_loop)
    return future.result(timeout=65)


@mcp.tool()
def browser_navigate(url: Annotated[str, Field(min_length=8, max_length=2048)]) -> str:
    """Navigate the persistent controlled Playwright browser to an HTTP or HTTPS URL."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Only absolute http:// and https:// URLs are allowed.")
    return _browser_call("browser_navigate", {"url": url})


@mcp.tool()
def browser_snapshot() -> str:
    """Read the accessibility snapshot of the current persistent browser page."""
    return _browser_call("browser_snapshot", {})


@mcp.tool()
def browser_click(element: Annotated[str, Field(min_length=1, max_length=500)]) -> str:
    """Click a visible browser element by its accessible description."""
    return _browser_call("browser_click", {"element": element})


@mcp.tool()
def browser_type(text: Annotated[str, Field(min_length=1, max_length=2000)]) -> str:
    """Type into the currently focused browser element."""
    return _browser_call("browser_type", {"text": text})


@mcp.tool()
def browser_press_key(
    key: Annotated[
        str,
        Field(
            pattern="^(Enter|Tab|Escape|Backspace|ArrowUp|ArrowDown|ArrowLeft|ArrowRight|Control[+]L)$"
        ),
    ],
) -> str:
    """Press a limited set of browser keyboard keys."""
    return _browser_call("browser_press_key", {"key": key})


def _kwin_dbus(method: str, *args: str) -> str:
    return run_checked(
        [
            "qdbus6",
            "org.chatgpt.DesktopControl",
            "/org/chatgpt/DesktopControl",
            f"org.chatgpt.DesktopControl.{method}",
            *args,
        ],
        timeout=5,
    )


def _kwin_refresh() -> list[dict]:
    # Trigger the KWin script's refresh shortcut, then read its cached window list.
    run_checked(
        [
            "qdbus6",
            "org.kde.kglobalaccel",
            "/component/kwin",
            "org.kde.kglobalaccel.Component.invokeShortcut",
            "DesktopControlRefreshV5",
        ]
    )
    import time

    time.sleep(0.25)
    raw = _kwin_dbus("GetWindows")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"KWin returned invalid window data: {exc}") from exc
    if not isinstance(data, list):
        raise RuntimeError("KWin returned an unexpected window list.")
    return data


def _match_window(windows: list[dict], match: str) -> dict | None:
    needle = match.casefold()
    # Exact application identifiers take precedence over title substrings.
    exact = next(
        (
            w
            for w in windows
            if needle == str(w.get("resourceClass", "")).casefold()
            or needle == str(w.get("resourceName", "")).casefold()
        ),
        None,
    )
    if exact:
        return exact
    return next((w for w in windows if needle in str(w.get("caption", "")).casefold()), None)


def _kwin_window_info(uuid: str) -> dict[str, str]:
    raw = run_checked(
        ["qdbus6", "org.kde.KWin", "/KWin", "org.kde.KWin.getWindowInfo", uuid], timeout=5
    )
    result = {}
    for line in raw.splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            result[key] = value
    return result


def _kwin_action(action: str, match: str) -> str:
    if not match or len(match) > 300:
        raise ValueError(
            "Provide a non-empty window title or application class (max 300 characters)."
        )
    windows = _kwin_refresh()
    initial = _match_window(windows, match)
    if not initial:
        raise ValueError(
            f"No open window matched {match!r}. "
            "Use window_list to inspect available titles and app classes."
        )
    info = _kwin_window_info(str(initial.get("uuid", ""))) if initial.get("uuid") else {}
    _kwin_dbus("SetCommand", json.dumps({"action": action, "match": match}))
    run_checked(
        [
            "qdbus6",
            "org.kde.kglobalaccel",
            "/component/kwin",
            "org.kde.kglobalaccel.Component.invokeShortcut",
            "DesktopControlCommandV5",
        ]
    )
    if action in ("maximize", "restore"):
        import time

        time.sleep(0.25)
        is_maximized = (
            info.get("maximizeHorizontal", "0") != "0" and info.get("maximizeVertical", "0") != "0"
        )
        if action == "maximize" and not is_maximized:
            run_checked(
                [
                    "qdbus6",
                    "org.kde.kglobalaccel",
                    "/component/kwin",
                    "org.kde.kglobalaccel.Component.invokeShortcut",
                    "Window Maximize",
                ]
            )
        elif action == "restore" and is_maximized:
            run_checked(
                [
                    "qdbus6",
                    "org.kde.kglobalaccel",
                    "/component/kwin",
                    "org.kde.kglobalaccel.Component.invokeShortcut",
                    "Window Restore",
                ]
            )
    import time

    target = None
    for _ in range(10):
        time.sleep(0.2)
        updated = _kwin_refresh()
        target = _match_window(updated, match)
        if action == "close" and target is None:
            return f"Confirmed closed: {initial.get('caption') or initial.get('resourceClass')}."
        if action == "focus" and target and target.get("active"):
            return f"Confirmed focused: {target.get('caption') or target.get('resourceClass')}."
        if action == "minimize" and target and target.get("minimized"):
            return f"Confirmed minimized: {target.get('caption') or target.get('resourceClass')}."
        if action == "maximize" and target:
            state = _kwin_window_info(str(target.get("uuid", "")))
            if (
                state.get("maximizeHorizontal", "0") != "0"
                and state.get("maximizeVertical", "0") != "0"
            ):
                return (
                    f"Confirmed maximized: {target.get('caption') or target.get('resourceClass')}."
                )
        if action == "restore" and target and not target.get("minimized"):
            state = _kwin_window_info(str(target.get("uuid", "")))
            if (
                state.get("maximizeHorizontal", "0") == "0"
                and state.get("maximizeVertical", "0") == "0"
            ):
                return (
                    f"Confirmed restored: {target.get('caption') or target.get('resourceClass')}."
                )
    window_name = initial.get("caption") or initial.get("resourceClass")
    raise RuntimeError(f"KWin did not confirm the requested {action} operation for {window_name}.")


@mcp.tool()
def window_list() -> str:
    """List open KDE windows with titles, application classes, PIDs, desktops and state."""
    windows = _kwin_refresh()
    return json.dumps(windows, ensure_ascii=False, indent=2)


@mcp.tool()
def window_focus(match: Annotated[str, Field(min_length=1, max_length=300)]) -> str:
    """Focus a window by title substring or exact app class (e.g. Brave or org.kde.konsole)."""
    return _kwin_action("focus", match)


@mcp.tool()
def window_switch(direction: Annotated[str, Field(pattern="^(next|previous)$")] = "next") -> str:
    """Switch to the next or previous KDE window using the desktop's Alt+Tab switcher."""
    keys = ["alt", "tab"] if direction == "next" else ["alt", "shift", "tab"]
    events = [f"{KEY_CODES[k]}:1" for k in keys]
    events += [f"{KEY_CODES[k]}:0" for k in reversed(keys)]
    run_checked(["ydotool", "key", *events])
    return f"Requested {direction} window switch through KDE's window switcher."


@mcp.tool()
def window_minimize(match: Annotated[str | None, Field(max_length=300)] = None) -> str:
    """Minimize a window matched by title/app class; omit match to minimize the active window."""
    if match:
        return _kwin_action("minimize", match)
    events = [f"{KEY_CODES[k]}:1" for k in ("super", "down")]
    events += [f"{KEY_CODES[k]}:0" for k in ("down", "super")]
    run_checked(["ydotool", "key", *events])
    return "Sent KDE's Meta+Down minimize shortcut to the active window."


@mcp.tool()
def window_maximize(match: Annotated[str | None, Field(max_length=300)] = None) -> str:
    """Maximize a window matched by title/app class; omit match to maximize the active window."""
    if match:
        return _kwin_action("maximize", match)
    events = [f"{KEY_CODES[k]}:1" for k in ("super", "up")]
    events += [f"{KEY_CODES[k]}:0" for k in ("up", "super")]
    run_checked(["ydotool", "key", *events])
    return "Sent KDE's Meta+Up maximize shortcut to the active window."


@mcp.tool()
def window_restore(match: Annotated[str, Field(min_length=1, max_length=300)]) -> str:
    """Restore a minimized or maximized window by title substring or application class."""
    return _kwin_action("restore", match)


@mcp.tool()
def window_close(match: Annotated[str | None, Field(max_length=300)] = None) -> str:
    """Close a matched window; omit match to send Alt+F4 to the active window."""
    if match:
        return _kwin_action("close", match)
    run_checked(["ydotool", "key", "56:1", "62:1", "62:0", "56:0"])
    return "Sent KDE's Alt+F4 close shortcut to the active window."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
