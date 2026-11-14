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

## Connecting MCP clients

The desktop server exposes the **MCP Streamable HTTP** transport at:

```text
http://127.0.0.1:8932/mcp
```

Add that URL in an MCP host that supports connecting to a remote Streamable HTTP server. The endpoint is loopback-only, so the MCP host must run on this same Linux machine (or use an explicitly configured secure tunnel; do not expose this service directly to the internet).

The separate Playwright MCP service is available at:

```text
http://127.0.0.1:8931/mcp
```

Connect to it separately only if you want to use the standalone Playwright MCP tools. The desktop server already integrates with this service internally for its `browser_*` tools.

### Client compatibility notes

- **Verified:** a standalone Python MCP SDK client initialized against `http://127.0.0.1:8932/mcp`, discovered all 19 tools, and successfully called `desktop_status`.
- **Not yet verified:** setup and tool invocation from individual GUI hosts (for example, Claude Desktop or ChatGPT). Their support for remote Streamable HTTP endpoints and their configuration screens vary by version. Follow the host's current documentation and use the endpoint above where remote HTTP MCP servers are supported.
- **Not a stdio server:** this project currently serves Streamable HTTP; clients that only accept stdio MCP servers need a compatible HTTP-to-stdio bridge or a stdio transport implementation, neither of which is included here.

### Verify a connection with the Python MCP SDK

From this project directory, run:

```bash
uv run python - <<'PY'
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client("http://127.0.0.1:8932/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            info = await session.initialize()
            tools = await session.list_tools()
            print(f"Connected to {info.serverInfo.name} {info.serverInfo.version}")
            print(f"Discovered {len(tools.tools)} tools")
            result = await session.call_tool("desktop_status", {})
            print(result.content)

asyncio.run(main())
PY
```
