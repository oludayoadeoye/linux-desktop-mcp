# Linux Desktop Control MCP

A local Python MCP server for controlling an EndeavourOS / Arch Linux KDE Plasma Wayland desktop, with window management and persistent Playwright browser automation.

## Features

- 19 MCP tools for screenshots, mouse/keyboard input, app launching, desktop status, browser automation, and KDE window management.
- MCP over stdio (agent-launched local process) or Streamable HTTP (loopback service).
- Installable `linux-desktop-mcp` command via uv tools or uvx.
- Optional one-file Linux executable build using PyInstaller.
- KWin JavaScript integration with a small session D-Bus bridge for window discovery and targeted window operations.
- Persistent headless Firefox context via Playwright MCP.

## Install as a CLI

Install directly from GitHub:

```bash
uv tool install git+https://github.com/oludayoadeoye/linux-desktop-mcp
linux-desktop-mcp --help
linux-desktop-mcp serve --transport stdio
```

Or run without installing persistently:

```bash
uvx --from git+https://github.com/oludayoadeoye/linux-desktop-mcp linux-desktop-mcp serve --transport stdio
```

## Full EndeavourOS / Arch setup

The Python CLI alone does not install system-level desktop dependencies or the Playwright/KWin sidecars. For the complete KDE Wayland setup, use the Arch installer:

```bash
git clone https://github.com/oludayoadeoye/linux-desktop-mcp.git
cd linux-desktop-mcp
./scripts/install-arch.sh
```

The installer creates and starts the Playwright MCP, KWin D-Bus bridge, and desktop MCP user services. Log out and back into KDE after installation so KWin loads its script package. See [the full installation guide](docs/INSTALL.md).

## Run modes

```bash
linux-desktop-mcp serve --transport stdio
linux-desktop-mcp serve --transport http --host 127.0.0.1 --port 8932
linux-desktop-mcp status
```

Stdio is the default and is intended for agents that launch MCP servers as subprocesses. HTTP is intended for local service integrations. The Arch installer configures HTTP on `127.0.0.1:8932/mcp`.

## Standalone executable

Build a Linux one-file executable on the target architecture:

```bash
./scripts/build-binary.sh
./dist/linux-desktop-mcp --help
```

The binary bundles Python dependencies only; it does not bundle KDE, D-Bus, ydotool, Spectacle, the KWin bridge, Playwright MCP, or Firefox. See [binary and runtime requirements](docs/INSTALL.md#standalone-linux-executable).

## Development

```bash
uv sync --locked --group dev
uv run ruff check .
uv run pytest -q
```

The automated tests mock external desktop/browser effects. GitHub Actions runs lint, tests, and Python compilation.

## Security

- The HTTP MCP endpoint binds to `127.0.0.1` by default.
- Application launching is allowlisted in `main.py`.
- Browser navigation accepts only absolute HTTP and HTTPS URLs.
- Desktop-control tools can interact with the user's active desktop. Connect only trusted MCP clients; do not expose these ports publicly.
