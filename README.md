# Linux Desktop Control MCP

A local Python MCP server for controlling an EndeavourOS / Arch Linux KDE Plasma Wayland desktop, with window management and persistent Playwright browser automation.

## Features

- 19 MCP tools for screenshots, mouse/keyboard input, app launching, desktop status, browser automation, and KDE window management.
- KWin JavaScript integration with a small session D-Bus bridge for window discovery and targeted window operations.
- Persistent headless Firefox context via Playwright MCP.
- Streamable HTTP transport, bound to loopback only.

## Quick install (EndeavourOS / Arch)

```bash
git clone https://github.com/oludayoadeoye/linux-desktop-mcp.git
cd linux-desktop-mcp
./scripts/install-arch.sh
```

Log out and back into KDE after installation so KWin loads the script package. For prerequisites, detailed setup, service management, verification, and uninstall steps, see [Installation guide](docs/INSTALL.md).

## MCP endpoints and clients

- Desktop MCP: `http://127.0.0.1:8932/mcp`
- Standalone Playwright MCP: `http://127.0.0.1:8931/mcp`

The desktop server integrates with Playwright internally. Most clients should connect only to the desktop endpoint. It uses MCP Streamable HTTP and binds to `127.0.0.1`, so the client must run on the same machine.

Client setup examples are documented for [Cursor](docs/INSTALL.md#cursor-direct-local-http), [ChatGPT desktop](docs/INSTALL.md#chatgpt-desktop-app-direct-local-http), and [Claude Desktop](docs/INSTALL.md#claude-desktop-stdio-bridge-to-local-http). ChatGPT web and Claude cloud connectors cannot directly reach a loopback-only server; use their documented secure tunnel or public HTTPS options only if you intentionally choose to make a remote connection available.

**Verification:** a Python MCP SDK client successfully initialized, discovered all 19 tools, and invoked `desktop_status`. GUI setup examples are based on the clients' published documentation; GUI setup has not been tested on every client. See the [full installation and client guide](docs/INSTALL.md).

## Development

```bash
uv sync --locked --group dev
uv run ruff check .
uv run pytest -q
```

The automated tests mock external desktop/browser effects. GitHub Actions runs lint, tests, and Python compilation for pushes and pull requests.

## Security notes

- Both HTTP MCP endpoints listen on `127.0.0.1` only.
- Application launching is allowlisted in `main.py`.
- Browser navigation accepts only absolute HTTP and HTTPS URLs.
- Desktop-control tools can interact with the user's active desktop. Connect only trusted MCP clients; do not expose these ports publicly.
