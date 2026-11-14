# Desktop Control MCP

A local Python MCP server with native desktop backends for KDE Plasma Wayland on Linux and macOS, plus persistent Playwright browser automation. MCP tool names and schemas stay consistent across operating systems while native backends handle input, screenshots, application launching, and window management.

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
- Installable `desktop-control-mcp` command, with backward-compatible `linux-desktop-mcp` alias, via uv tools or uvx.
- Optional one-file Linux executable build using PyInstaller.
- Native backend architecture: Linux KDE/Wayland and macOS Quartz/Accessibility.
- KWin JavaScript integration with a small session D-Bus bridge for Linux window discovery and targeted window operations.
- macOS input via Quartz events, screenshots via screencapture, and window operations via System Events Accessibility.
- Persistent headless Firefox context via Playwright MCP.

## macOS setup (initial native backend)

The macOS backend uses Quartz for mouse/keyboard events, screencapture for screenshots, open for application launching, and AppleScript/System Events for window operations.

Requirements: macOS 13+, Python 3.11+, uv, Node.js/npm, and a logged-in GUI session. From a cloned checkout:

~~~bash
uv sync --locked --group dev
npm install --global playwright-mcp playwright
playwright install firefox
~~~

Start the browser sidecar in one terminal:

~~~bash
playwright-mcp --port 8931 --host 127.0.0.1 --browser firefox --isolated --headless
~~~

Start the desktop MCP in another terminal:

~~~bash
uv run desktop-control-mcp serve --transport http --host 127.0.0.1 --port 8932
~~~

On first use, grant Accessibility to the terminal/agent host for mouse, keyboard and window control, and Screen Recording for screenshots under System Settings → Privacy & Security. Restart the MCP process after changing permissions.

The macOS backend has unit tests using mocked Quartz APIs, but it has not yet been exercised on a physical macOS host. Window-management behavior varies by application and its accessibility support. The current one-command release installer remains Linux x86_64 only; macOS users install from source with uv until native macOS release builds are added.

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
desktop-control-mcp serve --transport stdio
desktop-control-mcp serve --transport http --host 127.0.0.1 --port 8932
desktop-control-mcp status
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
