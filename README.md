# Linux Desktop Control MCP

A local Python MCP server for controlling an EndeavourOS / Arch Linux KDE Plasma Wayland desktop, with window management and persistent Playwright browser automation.

## Quick install (Linux x86_64)

Install the latest verified standalone CLI binary:

```bash
curl -fsSL https://raw.githubusercontent.com/oludayoadeoye/linux-desktop-mcp/master/install.sh | bash
```

The installer downloads the latest GitHub Release, verifies its SHA-256 digest against GitHub release metadata, and installs to `~/.local/bin`. If no prebuilt binary exists for the architecture, it falls back to a uv source installation. The one-command installer installs the CLI only; it does not provision KDE/Wayland dependencies or the Playwright/KWin sidecars.

**Repository visibility:** this repository is currently private, so the public `curl | bash` command above will only work after the repository is made public. For authorized private-repository access, clone with your GitHub credentials and run `bash install.sh` from the checkout; the script can use your authenticated `gh` session to fetch the release.

## Features

- 19 MCP tools for screenshots, mouse/keyboard input, app launching, desktop status, browser automation, and KDE window management.
- MCP over stdio (agent-launched local process) or Streamable HTTP (loopback service).
- Installable `linux-desktop-mcp` command via uv tools or uvx.
- Optional one-file Linux executable build using PyInstaller.
- KWin JavaScript integration with a small session D-Bus bridge for window discovery and targeted window operations.
- Persistent headless Firefox context via Playwright MCP.

## Full EndeavourOS / Arch setup

For the complete KDE Wayland setup, including system dependencies and user services, use the Arch installer:

```bash
git clone https://github.com/oludayoadeoye/linux-desktop-mcp.git
cd linux-desktop-mcp
./scripts/install-arch.sh
```

It creates and starts the Playwright MCP, KWin D-Bus bridge, and desktop MCP user services. Log out and back into KDE after installation so KWin loads its script package. See [the full installation guide](docs/INSTALL.md).

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

GitHub Actions builds the Linux x86_64 executable on Ubuntu 22.04 and smoke-tests it on Debian 12 and Debian 13 containers before publishing a SHA-256 manifest with tagged releases. The binary bundles Python dependencies only; it does not bundle KDE, D-Bus, ydotool, Spectacle, the KWin bridge, Playwright MCP, or Firefox. See [binary and runtime requirements](docs/INSTALL.md#standalone-linux-executable).

## Development

```bash
uv sync --locked --group dev
uv run ruff check .
uv run pytest -q
```

The automated tests mock external desktop/browser effects. GitHub Actions runs lint, tests, compilation, and packaging.

## Security

- The HTTP MCP endpoint binds to `127.0.0.1` by default.
- Application launching is allowlisted in `main.py`.
- Browser navigation accepts only absolute HTTP and HTTPS URLs.
- Desktop-control tools can interact with the user's active desktop. Connect only trusted MCP clients; do not expose these ports publicly.
