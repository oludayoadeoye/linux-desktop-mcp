# Linux Desktop Control MCP

A local-only Python MCP server for controlling an EndeavourOS / KDE Plasma Wayland desktop.

## Services

- Desktop MCP: `http://127.0.0.1:8932/mcp`
- Playwright MCP: `http://127.0.0.1:8931/mcp`
- KWin bridge: D-Bus session service `org.chatgpt.DesktopControl`

All network listeners bind to loopback only.

## Runtime

The project uses Python 3.11+ and `uv`. User-level systemd services manage the processes:

```bash
systemctl --user status desktop-control playwright-mcp kwin-desktop-bridge
systemctl --user restart desktop-control
journalctl --user -u desktop-control -f
```

KWin window support is provided by the installed script package:
`~/.local/share/kwin/scripts/linux-desktop-mcp`.
It is enabled in `~/.config/kwinrc` and reports window metadata through the session D-Bus bridge.

## Tools

### Desktop and input
- `desktop_screenshot`
- `desktop_status`
- `launch_application`
- `mouse_move`, `mouse_click`
- `keyboard_type`, `keyboard_hotkey`

### Windows
- `window_list` — titles, app IDs, PIDs, minimized/active state and UUID
- `window_focus` — title substring or exact app class/name
- `window_switch`
- `window_minimize`, `window_maximize`, `window_restore`, `window_close`

Targeted window operations are verified against KWin state before success is reported.

### Browser
- `browser_navigate`
- `browser_snapshot`
- `browser_click`
- `browser_type`
- `browser_press_key`

The desktop MCP keeps one Playwright MCP client session alive so browser state persists between calls.

## Security notes

- Both HTTP MCP endpoints listen on `127.0.0.1` only.
- Application launching is allowlisted in `main.py`.
- Browser navigation accepts only absolute HTTP and HTTPS URLs.
- This is a local desktop automation bridge, not a remote network service. Do not expose its ports publicly.
