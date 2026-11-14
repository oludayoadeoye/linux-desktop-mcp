"""Select the native backend for the current operating system."""

from __future__ import annotations

import sys

from .base import DesktopBackend


def get_backend() -> DesktopBackend:
    if sys.platform == "darwin":
        from .macos import MacOSBackend

        return MacOSBackend()
    if sys.platform == "win32":
        from .windows import WindowsBackend

        return WindowsBackend()
    if sys.platform.startswith("linux"):
        from .linux import LinuxBackend

        return LinuxBackend()
    raise RuntimeError(f"Unsupported desktop platform: {sys.platform}")
