# Desktop Control MCP

A local Python MCP server with native desktop backends for KDE Plasma Wayland on Linux, macOS, and Windows, plus persistent Playwright browser automation. MCP tool names and schemas stay consistent across operating systems while native backends handle input, screenshots, application launching, and window management.

## Quick install (Linux x86_64 / ARM64)

Install the latest verified standalone CLI binary:

```bash
curl -fsSL https://raw.githubusercontent.com/oludayoadeoye/linux-desktop-mcp/master/install.sh | bash
```

The installer detects x86_64 or ARM64 and downloads the matching Linux release asset, verifies its SHA-256 digest against GitHub release metadata, and installs it as `~/.local/bin/desktop-control-mcp`. Other Linux architectures can use the matching release binary directly or install from source with uv. The CLI-only installer does not provision KDE/Wayland dependencies or the Playwright/KWin sidecars.

## Features

- 19 MCP tools for screenshots, mouse/keyboard input, app launching, desktop status, browser automation, and KDE window management.
- MCP over stdio (agent-launched local process) or Streamable HTTP (loopback service).
- Installable `desktop-control-mcp` command, with backward-compatible `linux-desktop-mcp` alias, via uv tools or uvx.
- One-file standalone binaries for Linux x86_64/ARM64, Windows x64, and macOS Intel/Apple Silicon.
- Native backend architecture: Linux KDE/Wayland, macOS Quartz/Accessibility, and Windows Win32/PyAutoGUI.
- KWin JavaScript integration with a small session D-Bus bridge for Linux window discovery and targeted window operations.
- macOS input via Quartz events, screenshots via screencapture, and window operations via System Events Accessibility.
- Windows input and screenshots via PyAutoGUI, with window management through native Win32 APIs.
- Persistent headless Firefox context via Playwright MCP.

## macOS setup

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

The macOS backend has unit tests using mocked Quartz APIs, but it has not yet been exercised on a physical macOS host. Window-management behavior varies by application and its accessibility support. Release binaries are unsigned and are not notarized; macOS may require you to approve the app in Privacy & Security or remove the quarantine attribute after verifying the checksum.

## Windows setup

Requirements: Windows 10/11, running in the signed-in interactive desktop session. Download `desktop-control-mcp-windows-x86_64.exe` and `SHA256SUMS` from the [latest release](https://github.com/oludayoadeoye/linux-desktop-mcp/releases/latest), then verify it in PowerShell with `Get-FileHash .\desktop-control-mcp-windows-x86_64.exe -Algorithm SHA256`. Compare the hash with the matching line in `SHA256SUMS`. Rename the verified file to `desktop-control-mcp.exe` and place it in a directory on PATH. For source installation instead, use uv:

```powershell
git clone https://github.com/oludayoadeoye/linux-desktop-mcp.git
cd linux-desktop-mcp
uv sync --locked --group dev
uv run desktop-control-mcp serve --transport stdio
```

The Windows backend uses Win32 APIs for window enumeration, focus, minimize, maximize, restore, and close; PyAutoGUI handles screenshots, mouse input, and keyboard input. Applications are launched from a small allowlist (Notepad, Calculator, Terminal, Explorer, Edge, Chrome, Firefox, VS Code, Word, Excel, and Paint). Run the MCP host in the logged-in interactive session; Windows services running in session 0 cannot control the user desktop. This backend is covered by mocked unit tests and Windows CI, but still needs interactive validation on a physical Windows desktop.

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

## Standalone binaries

Every tagged release builds and smoke-tests five native executables:

| Release asset | Platform |
|---|---|
| `desktop-control-mcp-linux-x86_64` | Linux x86_64 (Ubuntu 22.04 glibc baseline; Debian 12/13 smoke-tested) |
| `desktop-control-mcp-linux-aarch64` | Linux ARM64 |
| `desktop-control-mcp-windows-x86_64.exe` | Windows x64 |
| `desktop-control-mcp-macos-x86_64` | macOS Intel |
| `desktop-control-mcp-macos-arm64` | macOS Apple Silicon |

All five assets are published with a single `SHA256SUMS` manifest. Download the matching asset and manifest from [GitHub Releases](https://github.com/oludayoadeoye/linux-desktop-mcp/releases/latest) and verify the SHA-256 before running it.

On EndeavourOS/Arch, use the Linux x86_64 or ARM64 asset matching your CPU. There is no separate Arch executable: the Linux x86_64 build uses an Ubuntu 22.04 glibc baseline and is smoke-tested on Debian 12/13, but the full desktop stack still depends on your distribution's KDE/Wayland, D-Bus and system packages. The Arch installer remains the recommended way to provision those services.

On macOS, download the asset matching Intel or Apple Silicon, make it executable with `chmod +x`, and run it from a logged-in GUI session. Grant Accessibility and Screen Recording permissions to the terminal/agent host. The binaries are currently unsigned and not notarized.

The Windows executable must be launched from the signed-in interactive desktop session; a Windows service running in Session 0 cannot control the user's desktop.

The executable bundles the Python application dependencies only. It does not bundle KDE, D-Bus, ydotool, Spectacle, the KWin bridge, Playwright MCP, or Firefox. See [binary and runtime requirements](docs/INSTALL.md#standalone-linux-executable).

Build locally on the target OS and CPU architecture with:

```bash
uv sync --locked --group build
uv run pyinstaller --clean --noconfirm --onefile --name desktop-control-mcp --collect-all mcp --collect-all pydantic --collect-submodules backends cli.py
```

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
