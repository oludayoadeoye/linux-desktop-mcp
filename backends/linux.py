"""Linux KDE/Wayland implementation of the desktop backend contract."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from mcp.server.fastmcp import Image


class LinuxBackend:
    name = "linux-kde"

    @staticmethod
    def _m():
        import main

        return main

    def screenshot(self):
        m = self._m()
        fd, name = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        p = Path(name)
        try:
            m.run_checked(["spectacle", "-f", "-b", "-n", "-o", str(p)], timeout=20)
            if not p.exists() or not p.stat().st_size:
                raise RuntimeError("Spectacle did not produce a screenshot")
            return Image(data=p.read_bytes(), format="png")
        finally:
            p.unlink(missing_ok=True)

    def _desktop_bounds(self):
        """Return the virtual desktop width and height in logical pixels."""
        m = self._m()
        output = m.run_checked(["kscreen-doctor", "-o"], timeout=5)
        output = re.sub(r"\x1b\[[0-9;]*m", "", output)
        geometries = []
        for block in re.split(r"(?m)^Output:", output)[1:]:
            if not re.search(r"(?m)^\s*enabled\s*$", block):
                continue
            match = re.search(
                r"(?m)^\s*Geometry:\s*(-?\d+),(-?\d+)\s+(\d+)x(\d+)\s*$",
                block,
            )
            if match:
                x, y, width, height = map(int, match.groups())
                geometries.append((x, y, x + width, y + height))
        if not geometries:
            raise RuntimeError("Could not determine enabled display geometry from kscreen-doctor.")
        left = min(item[0] for item in geometries)
        top = min(item[1] for item in geometries)
        right = max(item[2] for item in geometries)
        bottom = max(item[3] for item in geometries)
        return right - left, bottom - top

    def mouse_move(self, x, y):
        # ydotool's absolute input range is 0..65535, not screen pixels.
        width, height = self._desktop_bounds()
        absolute_x = round(max(0, min(x, width - 1)) * 65535 / max(1, width - 1))
        absolute_y = round(max(0, min(y, height - 1)) * 65535 / max(1, height - 1))
        self._m().run_checked(
            ["ydotool", "mousemove", "--absolute", "-x", str(absolute_x), "-y", str(absolute_y)]
        )
        return f"Mouse moved to ({x}, {y})."

    def mouse_click(self, button, clicks):
        m = self._m()
        for _ in range(clicks):
            m.run_checked(["ydotool", "click", m.BUTTONS[button]])
        return f"Performed {clicks} {button} click(s)."

    def keyboard_type(self, text):
        self._m().run_checked(["ydotool", "type", "--key-delay", "1", text], timeout=30)
        return f"Typed {len(text)} characters."

    def keyboard_hotkey(self, keys):
        m = self._m()
        keys = [k.lower() for k in keys]
        bad = [k for k in keys if k not in m.KEY_CODES]
        if bad:
            raise ValueError(f"Unsupported key name(s): {', '.join(bad)}")
        events = [f"{m.KEY_CODES[k]}:1" for k in keys] + [
            f"{m.KEY_CODES[k]}:0" for k in reversed(keys)
        ]
        m.run_checked(["ydotool", "key", *events])
        return f"Pressed {' + '.join(keys)}."

    def launch_application(self, application):
        app = {
            "finder": "dolphin",
            "terminal": "konsole",
            "safari": "firefox",
            "textedit": "kate",
            "vscode": "code",
        }.get(application, self._m().APP_ALLOWLIST.get(application, application))
        path = shutil.which(app)
        if not path:
            raise RuntimeError(f"{app} is not installed or not on PATH.")
        subprocess.Popen(
            [path],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return f"Launched {application}."

    def desktop_status(self):
        m = self._m()
        session = {
            k: os.environ.get(k, "")
            for k in ("XDG_CURRENT_DESKTOP", "XDG_SESSION_TYPE", "WAYLAND_DISPLAY")
        }
        display = "Unavailable"
        if shutil.which("kscreen-doctor"):
            try:
                display = m.run_checked(["kscreen-doctor", "-o"], timeout=5)
            except Exception as e:
                display = f"Display query unavailable: {e}"
        apps = ""
        if shutil.which("ps"):
            p = subprocess.run(
                ["ps", "-eo", "pid=,comm=,args="],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            apps = "\n".join(
                x.strip()
                for x in p.stdout.splitlines()
                if any(n in x.lower() for n in m.APP_ALLOWLIST)
            )[:4000]
        return (
            f"Backend: {self.name}\nSession: {session}\n"
            f"Displays:\n{display}\nRunning apps:\n{apps or 'None detected'}"
        )

    def window_list(self):
        return json.dumps(self._m()._kwin_refresh(), ensure_ascii=False, indent=2)

    def window_focus(self, match):
        return self._m()._kwin_action("focus", match)

    def window_switch(self, direction):
        m = self._m()
        keys = ["alt", "tab"] if direction == "next" else ["alt", "shift", "tab"]
        events = [f"{m.KEY_CODES[k]}:1" for k in keys] + [
            f"{m.KEY_CODES[k]}:0" for k in reversed(keys)
        ]
        m.run_checked(["ydotool", "key", *events])
        return f"Requested {direction} window switch."

    def _action(self, action, match):
        m = self._m()
        if match:
            return m._kwin_action(action, match)
        if action == "close":
            m.run_checked(["ydotool", "key", "56:1", "62:1", "62:0", "56:0"])
            return "Sent KDE Alt+F4 to active window."
        keys = {"minimize": ["super", "down"], "maximize": ["super", "up"]}[action]
        events = [f"{m.KEY_CODES[k]}:1" for k in keys] + [
            f"{m.KEY_CODES[k]}:0" for k in reversed(keys)
        ]
        m.run_checked(["ydotool", "key", *events])
        return f"Sent KDE Meta+{keys[1]} to active window."

    def window_minimize(self, match=None):
        return self._action("minimize", match)

    def window_maximize(self, match=None):
        return self._action("maximize", match)

    def window_restore(self, match):
        return self._m()._kwin_action("restore", match)

    def window_close(self, match=None):
        return self._action("close", match)
