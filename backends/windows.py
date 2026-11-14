"""Native Windows desktop backend using Win32 window APIs and PyAutoGUI input."""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
from ctypes import wintypes


class WindowsBackend:
    name = "windows"
    APP_ALLOWLIST = {
        "notepad": "notepad.exe", "calculator": "calc.exe",
        "terminal": "wt.exe", "cmd": "cmd.exe", "powershell": "powershell.exe",
        "explorer": "explorer.exe", "edge": "msedge.exe", "chrome": "chrome.exe",
        "firefox": "firefox.exe", "vscode": "code.exe", "word": "winword.exe",
        "excel": "excel.exe", "paint": "mspaint.exe",
    }
    KEY_ALIASES = {
        "command": "win", "super": "win", "escape": "esc",
        "return": "enter", "delete": "backspace",
    }
    SW_MINIMIZE, SW_RESTORE, SW_MAXIMIZE = 6, 9, 3
    WM_CLOSE = 0x0010

    def __init__(self):
        if os.name != "nt":
            raise RuntimeError("The Windows backend can only run on Windows.")
        try:
            import pyautogui
        except ImportError as exc:
            raise RuntimeError("Install the Windows desktop dependency with uv sync.") from exc
        self.gui = pyautogui
        self.user32 = ctypes.windll.user32
        self._configure_win32_signatures()

    def _configure_win32_signatures(self):
        u = self.user32
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        u.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        u.EnumWindows.restype = wintypes.BOOL
        u.IsWindowVisible.argtypes = [wintypes.HWND]
        u.IsWindowVisible.restype = wintypes.BOOL
        u.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        u.GetWindowTextLengthW.restype = ctypes.c_int
        u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetWindowTextW.restype = ctypes.c_int
        u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        u.GetWindowThreadProcessId.restype = wintypes.DWORD
        u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        u.GetWindowRect.restype = wintypes.BOOL
        u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetClassNameW.restype = ctypes.c_int
        u.GetForegroundWindow.restype = wintypes.HWND
        u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        u.ShowWindow.restype = wintypes.BOOL
        u.SetForegroundWindow.argtypes = [wintypes.HWND]
        u.SetForegroundWindow.restype = wintypes.BOOL
        u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        u.PostMessageW.restype = wintypes.BOOL
        u.GetSystemMetrics.argtypes = [ctypes.c_int]
        u.GetSystemMetrics.restype = ctypes.c_int

    def screenshot(self):
        from io import BytesIO

        from mcp.server.fastmcp import Image
        output = BytesIO()
        self.gui.screenshot().save(output, format="PNG")
        return Image(data=output.getvalue(), format="png")

    def mouse_move(self, x, y):
        self.gui.moveTo(x, y)
        return f"Mouse moved to ({x}, {y})."

    def mouse_click(self, button, clicks):
        self.gui.click(clicks=clicks, button=button)
        return f"Performed {clicks} {button} click(s)."

    def keyboard_type(self, text):
        self.gui.write(text, interval=0.001)
        return f"Typed {len(text)} characters."

    def keyboard_hotkey(self, keys):
        normalized = [self.KEY_ALIASES.get(k.lower(), k.lower()) for k in keys]
        try:
            self.gui.hotkey(*normalized)
        except Exception as exc:
            raise ValueError(f"Unsupported Windows hotkey: {' + '.join(keys)}") from exc
        return f"Pressed {' + '.join(keys)}."

    def launch_application(self, application):
        executable = self.APP_ALLOWLIST.get(application.lower())
        if not executable:
            raise ValueError(f"Application {application!r} is not in the Windows allowlist.")
        try:
            subprocess.Popen([executable], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        except OSError as exc:
            raise RuntimeError(f"Could not launch {application}: {exc}") from exc
        return f"Launched {application}."

    def _class_name(self, hwnd):
        name = ctypes.create_unicode_buffer(256)
        self.user32.GetClassNameW(hwnd, name, len(name))
        return name.value

    def _windows(self):
        rows = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def visit(hwnd, _):
            if not self.user32.IsWindowVisible(hwnd):
                return True
            length = self.user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            title = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, title, length + 1)
            pid = wintypes.DWORD()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            rect = wintypes.RECT()
            self.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            class_name = self._class_name(hwnd)
            foreground = self.user32.GetForegroundWindow()
            foreground_id = foreground if isinstance(foreground, int) else (foreground.value or 0)
            rows.append({
                "windowId": int(hwnd), "caption": title.value,
                "resourceClass": class_name, "resourceName": class_name,
                "pid": int(pid.value),
                "bounds": {"X": rect.left, "Y": rect.top,
                           "Width": rect.right - rect.left, "Height": rect.bottom - rect.top},
                "active": int(hwnd) == int(foreground_id),
            })
            return True

        self.user32.EnumWindows(callback_type(visit), 0)
        return rows

    @staticmethod
    def _match(rows, match):
        needle = match.casefold()
        return next((w for w in rows if w["resourceClass"].casefold() == needle), None) or next(
            (w for w in rows if needle in w["caption"].casefold()), None
        )

    def _target(self, match=None):
        rows = self._windows()
        target = self._match(rows, match) if match else next((w for w in rows if w["active"]), None)
        if not target:
            raise ValueError(f"No open window matched {match!r}." if match else "No active window.")
        return target

    def window_list(self):
        return json.dumps(self._windows(), ensure_ascii=False, indent=2)

    def window_focus(self, match):
        target = self._target(match)
        hwnd = wintypes.HWND(target["windowId"])
        self.user32.ShowWindow(hwnd, self.SW_RESTORE)
        if not self.user32.SetForegroundWindow(hwnd):
            raise RuntimeError(f"Windows denied foreground focus for {target['caption']!r}.")
        return f"Focused {target['resourceClass']} window {target['caption']!r}."

    def window_switch(self, direction):
        if direction == "next":
            self.gui.hotkey("alt", "tab")
        else:
            self.gui.hotkey("alt", "shift", "tab")
        return f"Requested {direction} window switch."

    def _operate(self, match, operation):
        target = self._target(match)
        hwnd = wintypes.HWND(target["windowId"])
        command = {"minimize": self.SW_MINIMIZE, "maximize": self.SW_MAXIMIZE,
                   "restore": self.SW_RESTORE}.get(operation)
        if operation == "close":
            if not self.user32.PostMessageW(hwnd, self.WM_CLOSE, 0, 0):
                raise RuntimeError(f"Could not send close request to {target['caption']!r}.")
        else:
            self.user32.ShowWindow(hwnd, command)
        return f"Requested {operation} for {target['resourceClass']} window {target['caption']!r}."

    def window_minimize(self, match=None):
        return self._operate(match, "minimize")

    def window_maximize(self, match=None):
        return self._operate(match, "maximize")

    def window_restore(self, match):
        return self._operate(match, "restore")

    def window_close(self, match=None):
        return self._operate(match, "close")

    def desktop_status(self):
        version = subprocess.run(["cmd", "/c", "ver"], capture_output=True,
                                 text=True, check=False).stdout.strip()
        width, height = self.user32.GetSystemMetrics(0), self.user32.GetSystemMetrics(1)
        apps = sorted({w["resourceClass"] for w in self._windows() if w["resourceClass"]})
        return (f"Backend: {self.name}\nWindows: {version}\n"
                f"Primary display: {width}x{height}\nVisible applications: {', '.join(apps)}")
