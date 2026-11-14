"""Native macOS backend: Quartz input/capture and Accessibility window control."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


class MacOSBackend:
    name = "macos"
    APP_ALLOWLIST = {
        "firefox": "Firefox",
        "brave": "Brave Browser",
        "finder": "Finder",
        "terminal": "Terminal",
        "safari": "Safari",
        "textedit": "TextEdit",
        "vscode": "Visual Studio Code",
        "dolphin": "Dolphin",
        "konsole": "Konsole",
        "kate": "Kate",
        "spectacle": "Screenshot",
        "systemsettings": "System Settings",
    }
    KEY_CODES = {
        "a": 0,
        "s": 1,
        "d": 2,
        "f": 3,
        "h": 4,
        "g": 5,
        "z": 6,
        "x": 7,
        "c": 8,
        "v": 9,
        "b": 11,
        "q": 12,
        "w": 13,
        "e": 14,
        "r": 15,
        "y": 16,
        "t": 17,
        "1": 18,
        "2": 19,
        "3": 20,
        "4": 21,
        "6": 22,
        "5": 23,
        "equal": 24,
        "9": 25,
        "7": 26,
        "minus": 27,
        "8": 28,
        "0": 29,
        "o": 31,
        "u": 32,
        "i": 34,
        "p": 35,
        "enter": 36,
        "l": 37,
        "j": 38,
        "k": 40,
        "n": 45,
        "m": 46,
        "tab": 48,
        "space": 49,
        "backspace": 51,
        "delete": 51,
        "escape": 53,
        "super": 55,
        "command": 55,
        "shift": 56,
        "alt": 58,
        "ctrl": 59,
        "left": 123,
        "right": 124,
        "down": 125,
        "up": 126,
        "home": 115,
        "end": 119,
        "pageup": 116,
        "pagedown": 121,
        "f11": 103,
        "f12": 111,
    }
    MODIFIERS = {
        "command": 1 << 20,
        "super": 1 << 20,
        "shift": 1 << 17,
        "alt": 1 << 19,
        "ctrl": 1 << 18,
    }
    BUTTONS = {"left": 0, "right": 1, "middle": 2}

    def __init__(self):
        try:
            import Quartz
        except ImportError as exc:
            raise RuntimeError(
                "Install the macOS Quartz bindings: python -m pip install pyobjc-framework-Quartz"
            ) from exc
        self.q = Quartz
        self._saved_bounds = {}
        self._saved_bounds = {}

    @staticmethod
    def _osascript(script):
        p = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=12, check=False
        )
        if p.returncode:
            raise RuntimeError(p.stderr.strip() or "AppleScript automation failed")
        return p.stdout.strip()

    @staticmethod
    def _quote(value):
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def screenshot(self):
        fd, name = tempfile.mkstemp(prefix="desktop-control-", suffix=".png")
        os.close(fd)
        path = Path(name)
        try:
            p = subprocess.run(
                ["screencapture", "-x", str(path)],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if p.returncode or not path.exists() or not path.stat().st_size:
                raise RuntimeError(
                    p.stderr.strip() or "Grant Screen Recording permission to the MCP host."
                )
            from mcp.server.fastmcp import Image

            return Image(data=path.read_bytes(), format="png")
        finally:
            path.unlink(missing_ok=True)

    def mouse_move(self, x, y):
        q = self.q
        e = q.CGEventCreateMouseEvent(
            None, q.kCGEventMouseMoved, q.CGPointMake(x, y), q.kCGMouseButtonLeft
        )
        q.CGEventPost(q.kCGHIDEventTap, e)
        return f"Mouse moved to ({x}, {y})."

    def mouse_click(self, button, clicks):
        q = self.q
        point = q.CGEventGetLocation(q.CGEventCreate(None))
        b = self.BUTTONS[button]
        downs = [q.kCGEventLeftMouseDown, q.kCGEventRightMouseDown, q.kCGEventOtherMouseDown]
        ups = [q.kCGEventLeftMouseUp, q.kCGEventRightMouseUp, q.kCGEventOtherMouseUp]
        for n in range(clicks):
            for typ in (downs[b], ups[b]):
                e = q.CGEventCreateMouseEvent(None, typ, point, b)
                q.CGEventSetIntegerValueField(e, q.kCGMouseEventClickState, n + 1)
                q.CGEventPost(q.kCGHIDEventTap, e)
        return f"Performed {clicks} {button} click(s)."

    def keyboard_type(self, text):
        q = self.q
        for chunk_start in range(0, len(text), 20):
            chunk = text[chunk_start : chunk_start + 20]
            down = q.CGEventCreateKeyboardEvent(None, 0, True)
            q.CGEventKeyboardSetUnicodeString(down, len(chunk), chunk)
            up = q.CGEventCreateKeyboardEvent(None, 0, False)
            q.CGEventKeyboardSetUnicodeString(up, len(chunk), chunk)
            q.CGEventPost(q.kCGHIDEventTap, down)
            q.CGEventPost(q.kCGHIDEventTap, up)
        return f"Typed {len(text)} characters."

    def keyboard_hotkey(self, keys):
        keys = [k.lower() for k in keys]
        bad = [k for k in keys if k not in self.KEY_CODES]
        if bad:
            raise ValueError(f"Unsupported key name(s): {', '.join(bad)}")
        regular = [k for k in keys if k not in self.MODIFIERS]
        if len(regular) != 1:
            raise ValueError("Provide one non-modifier key and optional modifiers.")
        flags = 0
        for key in keys:
            flags |= self.MODIFIERS.get(key, 0)
        q = self.q
        code = self.KEY_CODES[regular[0]]
        for down in (True, False):
            e = q.CGEventCreateKeyboardEvent(None, code, down)
            q.CGEventSetFlags(e, flags)
            q.CGEventPost(q.kCGHIDEventTap, e)
        return f"Pressed {' + '.join(keys)}."

    def launch_application(self, application):
        app = self.APP_ALLOWLIST[application]
        p = subprocess.run(
            ["open", "-a", app], capture_output=True, text=True, timeout=10, check=False
        )
        if p.returncode:
            raise RuntimeError(p.stderr.strip() or f"Could not launch {app}.")
        return f"Launched {application}."

    def desktop_status(self):
        q = self.q
        _, _, count = q.CGGetActiveDisplayList(0, None, None)
        displays = []
        if count:
            err, ids, actual = q.CGGetActiveDisplayList(count, None, None)
            if err == 0:
                for did in ids[:actual]:
                    b = q.CGDisplayBounds(did)
                    displays.append(
                        {
                            "id": int(did),
                            "width": int(q.CGDisplayPixelsWide(did)),
                            "height": int(q.CGDisplayPixelsHigh(did)),
                            "x": b.origin.x,
                            "y": b.origin.y,
                        }
                    )
        apps = self._osascript(
            'tell application "System Events" to get name of every process '
            "whose background only is false"
        )
        version = subprocess.run(
            ["sw_vers", "-productVersion"], capture_output=True, text=True, check=False
        ).stdout.strip()
        return (
            f"Backend: {self.name}\nmacOS: {version}\n"
            f"Displays: {json.dumps(displays)}\nRunning apps: {apps}"
        )

    def _windows(self):
        q = self.q
        opts = q.kCGWindowListOptionOnScreenOnly | q.kCGWindowListExcludeDesktopElements
        rows = q.CGWindowListCopyWindowInfo(opts, q.kCGNullWindowID) or []
        result = []
        for row in rows:
            if row.get(q.kCGWindowLayer, 0) != 0:
                continue
            title = row.get(q.kCGWindowName, "")
            owner = row.get(q.kCGWindowOwnerName, "")
            if not owner:
                continue
            result.append(
                {
                    "windowId": int(row.get(q.kCGWindowNumber, 0)),
                    "caption": title,
                    "resourceClass": owner,
                    "resourceName": owner,
                    "pid": int(row.get(q.kCGWindowOwnerPID, 0)),
                    "bounds": q.CGWindowBounds(row),
                    "active": False,
                }
            )
        return result

    @staticmethod
    def _match(rows, match):
        n = match.casefold()
        return next((w for w in rows if w["resourceClass"].casefold() == n), None) or next(
            (w for w in rows if n in w["caption"].casefold()), None
        )

    def window_list(self):
        return json.dumps(self._windows(), ensure_ascii=False, indent=2)

    def window_focus(self, match):
        w = self._match(self._windows(), match)
        if not w:
            raise ValueError(f"No open window matched {match!r}.")
        self._osascript(f'tell application "{self._quote(w["resourceClass"])}" to activate')
        return f"Activated {w['resourceClass']}."

    def window_switch(self, direction):
        return self.keyboard_hotkey(
            ["command", "tab"] if direction == "next" else ["command", "shift", "tab"]
        )

    def _target(self, match):
        rows = self._windows()
        w = self._match(rows, match) if match else (rows[0] if rows else None)
        if not w:
            raise ValueError(
                f"No open window matched {match!r}." if match else "No visible windows."
            )
        return w

    def _operate(self, match, operation):
        w = self._target(match)
        pid = w["pid"]
        title = w["caption"]
        try:
            process = f"(first process whose unix id is {pid})"
            window_ref = (
                f'(first window whose name is "{self._quote(title)}")' if title else "window 1"
            )
            if operation == "close":
                script = (
                    'tell application "System Events" to tell '
                    + process
                    + f' to click (first button of {window_ref} whose subrole is "AXCloseButton")'
                )
            elif operation == "minimize":
                script = (
                    'tell application "System Events" to tell '
                    + process
                    + f' to set value of attribute "AXMinimized" of {window_ref} to true'
                )
            elif operation == "restore":
                saved = self._saved_bounds.pop(w["windowId"], None)
                if saved:
                    x, y, width, height = saved
                    script = (
                        'tell application "System Events" to tell '
                        + process
                        + (
                            f" to tell window 1 to set bounds to "
                            f"{{{x}, {y}, {x + width}, {y + height}}}"
                        )
                    )
                else:
                    script = (
                        'tell application "System Events" to tell '
                        + process
                        + f' to set value of attribute "AXMinimized" of {window_ref} to false'
                    )
            elif operation == "maximize":
                row_bounds = w.get("bounds", {})
                if row_bounds:
                    self._saved_bounds[w["windowId"]] = (
                        row_bounds.get("X", 0),
                        row_bounds.get("Y", 0),
                        row_bounds.get("Width", 800),
                        row_bounds.get("Height", 600),
                    )
                _, _, count = self.q.CGGetActiveDisplayList(0, None, None)
                _, display_ids, _ = self.q.CGGetActiveDisplayList(count, None, None)
                bounds = self.q.CGDisplayBounds(display_ids[0])
                width = int(bounds.size.width)
                height = int(bounds.size.height)
                script = (
                    'tell application "System Events" to tell '
                    + process
                    + f" to tell {window_ref} to set bounds to {{0, 25, {width}, {height}}}"
                )
            else:
                raise ValueError(operation)
            self._osascript(script)
        except RuntimeError as exc:
            raise RuntimeError(
                f"Could not {operation} {title!r}. Grant Accessibility permission "
                "in System Settings > Privacy & Security > Accessibility."
            ) from exc
        return f"Requested {operation} for {w['resourceClass']} window {title!r}."

    def window_minimize(self, match=None):
        return self._operate(match, "minimize")

    def window_maximize(self, match=None):
        return self._operate(match, "maximize")

    def window_restore(self, match):
        return self._operate(match, "restore")

    def window_close(self, match=None):
        return self._operate(match, "close")
