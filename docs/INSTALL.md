# Installation

## Quick CLI installation (Linux x86_64 / ARM64)

Install the latest standalone executable:

```bash
curl -fsSL https://raw.githubusercontent.com/oludayoadeoye/linux-desktop-mcp/master/install.sh | bash
```

The script downloads the latest GitHub Release, verifies its SHA-256 digest against GitHub release metadata, and installs to `~/.local/bin` without sudo. Set `INSTALL_DIR` to override the destination. If no binary exists for the architecture, it falls back to a uv source installation.

The one-command installer installs the CLI only; it does not provision KDE/Wayland dependencies, the KWin bridge, Playwright MCP, or Firefox.

## Standalone binaries for other platforms

Tagged releases publish five native executables and a SHA-256 manifest:

| Asset | Target |
|---|---|
| `desktop-control-mcp-linux-x86_64` | Linux x86_64 |
| `desktop-control-mcp-linux-aarch64` | Linux ARM64 |
| `desktop-control-mcp-windows-x86_64.exe` | Windows x64 |
| `desktop-control-mcp-macos-x86_64` | macOS Intel |
| `desktop-control-mcp-macos-arm64` | macOS Apple Silicon |

Download the correct executable and `SHA256SUMS` from [the latest GitHub release](https://github.com/oludayoadeoye/linux-desktop-mcp/releases/latest). Verify the file before running it.

**Linux (including EndeavourOS/Arch):**

```bash
grep 'desktop-control-mcp-linux-x86_64' SHA256SUMS | sha256sum -c -
chmod +x desktop-control-mcp-linux-x86_64
./desktop-control-mcp-linux-x86_64 --help
```

The Linux x86_64 executable is built on Ubuntu 22.04 for a conservative glibc baseline and smoke-tested in Debian 12 and 13. Arch does not need a separate executable; the KDE/Wayland system dependencies still need to be installed separately. Use the ARM64 asset on ARM64 Linux.

**macOS:**

```bash
grep 'desktop-control-mcp-macos-arm64' SHA256SUMS | shasum -a 256 -c -
chmod +x desktop-control-mcp-macos-arm64  # Apple Silicon; use x86_64 on Intel
./desktop-control-mcp-macos-arm64 --help
```

The macOS executables are currently unsigned and not notarized. macOS may show a Gatekeeper warning; only approve the binary after verifying its checksum. Grant Accessibility and Screen Recording permissions to the terminal or agent host.

**Windows PowerShell:**

```powershell
Get-FileHash .\desktop-control-mcp-windows-x86_64.exe -Algorithm SHA256
.\desktop-control-mcp-windows-x86_64.exe --help
```

Compare the displayed hash with the matching entry in `SHA256SUMS`. The executable must run in the signed-in interactive desktop session, not as a Session 0 Windows service.

These are standalone CLI binaries, not full desktop-stack installers. They do not install Playwright MCP, Firefox, KDE/Wayland tools, or the KWin bridge.


Verify:

```bash
linux-desktop-mcp --help
linux-desktop-mcp status
```

If the command is not found, add `~/.local/bin` to PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

---

# Installation on EndeavourOS / Arch Linux

This guide installs the desktop MCP, its KWin D-Bus bridge, and the isolated headless Playwright browser service for a **KDE Plasma Wayland** session.

## Requirements

- EndeavourOS or Arch Linux, with KDE Plasma (Wayland session)
- A logged-in graphical desktop session and a working user D-Bus session
- `sudo` access for system packages
- Internet access for Python and Node dependencies and the Firefox browser binary

The installer uses pacman for system packages, `uv` for Python dependencies, and npm for the Playwright MCP server.

## 1. Get the project

```bash
git clone https://github.com/oludayoadeoye/linux-desktop-mcp.git
cd linux-desktop-mcp
```

## 2. Run the installer

```bash
chmod +x scripts/install-arch.sh
./scripts/install-arch.sh
```

The installer:

1. Installs Python, D-Bus/GObject bindings, Node.js/npm, Git and uv.
2. Installs the `playwright-mcp` and `playwright` npm packages for your user.
3. Downloads the Playwright Firefox browser.
4. Creates the locked Python environment, including test/lint dependencies.
5. Installs the KWin script package and enables it in `kwinrc`.
6. Creates and enables three user systemd services.

Log out of KDE and log back in after installation so KWin loads the newly installed script package. The user services should then start automatically.

## 3. Check service health

```bash
systemctl --user status desktop-control playwright-mcp kwin-desktop-bridge
systemctl --user is-active desktop-control playwright-mcp kwin-desktop-bridge
ss -ltn | grep -E '8931|8932'
```

Expected listeners are loopback-only:

- Desktop MCP: `http://127.0.0.1:8932/mcp`
- Playwright MCP: `http://127.0.0.1:8931/mcp`

Useful operations:

```bash
systemctl --user restart desktop-control
systemctl --user restart playwright-mcp
systemctl --user restart kwin-desktop-bridge
journalctl --user -u desktop-control -f
journalctl --user -u playwright-mcp -f
journalctl --user -u kwin-desktop-bridge -f
```

## 4. Connect an MCP client

The desktop server uses **MCP Streamable HTTP** at:

```text
http://127.0.0.1:8932/mcp
```

The client must run on this same machine because the endpoint binds to `127.0.0.1`. The Playwright endpoint at `http://127.0.0.1:8931/mcp` is optional as a separate connection; the desktop server already uses it internally.

### Cursor (direct local HTTP)

Cursor supports Streamable HTTP and can connect directly to a local URL. Merge this entry into `~/.cursor/mcp.json` (or the project's `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "linux-desktop-control": {
      "url": "http://127.0.0.1:8932/mcp"
    }
  }
}
```

Save the file, then open Cursor's MCP/Customize panel and enable the server. See the [Cursor MCP documentation](https://cursor.com/docs/mcp).

### ChatGPT desktop app (direct local HTTP)

The ChatGPT desktop app documents support for local MCP servers using Streamable HTTP:

1. Open ChatGPT desktop **Settings**.
2. Open **MCP servers**.
3. Select **Add server**.
4. Choose **Streamable HTTP** and enter `http://127.0.0.1:8932/mcp`.
5. Save and restart/reload the client if prompted.

The ChatGPT web app is different: a cloud-hosted connection cannot reach this machine's loopback address. For ChatGPT web custom MCP connections, use OpenAI's **Secure MCP Tunnel** or a secured, publicly reachable HTTPS deployment. Do not expose port 8932 directly to the internet. See [ChatGPT MCP setup](https://learn.chatgpt.com/docs/extend/mcp) and [OpenAI's MCP server guide](https://developers.openai.com/api/docs/guides/tools-connectors-mcp).

### Claude Desktop (stdio bridge to local HTTP)

Claude Desktop's local `claude_desktop_config.json` launches stdio processes. Use `mcp-remote` as a local stdio-to-Streamable-HTTP bridge. Node.js 18+ and npm/npx are required (installed by this guide's installer):

```json
{
  "mcpServers": {
    "linux-desktop-control": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://127.0.0.1:8932/mcp",
        "--allow-http"
      ]
    }
  }
}
```

On Linux, the config is usually `~/.config/Claude/claude_desktop_config.json`. Merge the entry into the existing `mcpServers` object; do not overwrite other servers. Fully quit and restart Claude Desktop. `--allow-http` is required for this loopback HTTP development endpoint; do not use this flag for an untrusted public URL. See the [mcp-remote project](https://github.com/punkpeye/mcp-remote) and [Claude's remote MCP connector guide](https://support.anthropic.com/en/articles/11503834-building-custom-integrations-via-remote-mcp).

Claude's cloud-based custom connector is not a way to reach this loopback URL: Anthropic's cloud connects from its own infrastructure. That option requires a publicly reachable HTTPS endpoint and is intentionally not enabled by this local-only setup.

### Other clients

Any client that can connect to a local Streamable HTTP URL can use the direct endpoint. Clients limited to stdio can use an equivalent local bridge such as `mcp-remote`. Check each client's current transport and configuration documentation before assuming compatibility.

### Verification status

The Python MCP SDK client has been tested end-to-end: initialize, list all 19 tools, and call `desktop_status`. The Cursor, ChatGPT desktop, and Claude Desktop configuration examples above are documented from their published client documentation, but their GUI setup has **not** been tested on every host in this project.

## 5. Verify the MCP protocol and tools

Run this from the project directory:

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
            if result.isError:
                raise RuntimeError(result.content)
            print(result.content)

asyncio.run(main())
PY
```

A successful check initializes the MCP session, discovers the tools, and invokes `desktop_status`.

## 6. Run automated tests and lint

```bash
uv sync --locked --group dev
uv run ruff check .
uv run pytest -q
```

Tests mock desktop commands, browser calls, and KWin interactions. They do not manipulate the real desktop.

## Uninstall / disable services

```bash
systemctl --user disable --now desktop-control playwright-mcp kwin-desktop-bridge
rm -f ~/.config/systemd/user/desktop-control.service
rm -f ~/.config/systemd/user/playwright-mcp.service
rm -f ~/.config/systemd/user/kwin-desktop-bridge.service
systemctl --user daemon-reload
```

Optionally remove the installed KWin package and disable its plugin:

```bash
rm -rf ~/.local/share/kwin/scripts/linux-desktop-mcp
kwriteconfig6 --file kwinrc --group Plugins --key linux-desktop-mcpEnabled false
```

The uninstaller intentionally does not remove Node/npm packages, Firefox browser caches, uv, or system packages because they may be used by other projects.

## Security

- Both HTTP services bind to loopback, not the LAN.
- Do not change the host to `0.0.0.0` or expose either port publicly.
- The desktop server can type into applications, click, and close windows. Connect only trusted MCP clients.
- Browser navigation accepts HTTP and HTTPS URLs; treat browser tools as privileged access to the local browser context.


## 7. Install as a uv CLI (without cloning manually)

The project publishes a console command named `linux-desktop-mcp`. Install it directly from GitHub:

```bash
uv tool install git+https://github.com/oludayoadeoye/linux-desktop-mcp
linux-desktop-mcp --help
linux-desktop-mcp status
```

To run it ephemerally without a persistent tool installation:

```bash
uvx --from git+https://github.com/oludayoadeoye/linux-desktop-mcp linux-desktop-mcp --help
uvx --from git+https://github.com/oludayoadeoye/linux-desktop-mcp linux-desktop-mcp serve --transport stdio
```

For development from a checkout:

```bash
uv sync --locked --group dev
uv run linux-desktop-mcp serve --transport stdio
uv run linux-desktop-mcp serve --transport http --host 127.0.0.1 --port 8932
uv run linux-desktop-mcp status
uv run linux-desktop-mcp test
```

The default transport is stdio, which is suitable for agents that launch a local MCP process. HTTP is opt-in. Keep the HTTP host on loopback unless you have deliberately configured an authenticated, secured remote deployment.

### Agent configuration (stdio)

Cursor and Claude Desktop support local stdio MCP processes. Merge this server entry into the relevant client's existing MCP configuration. Use the absolute executable path returned by `command -v linux-desktop-mcp` if the client does not inherit your shell PATH.

```json
{
  "mcpServers": {
    "linux-desktop-control": {
      "command": "linux-desktop-mcp",
      "args": ["serve", "--transport", "stdio"]
    }
  }
}
```

For a uv-managed install where the client cannot resolve the executable, use:

```json
{
  "mcpServers": {
    "linux-desktop-control": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/oludayoadeoye/linux-desktop-mcp",
        "linux-desktop-mcp",
        "serve",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

### Standalone Linux executable

A one-file PyInstaller build can be produced on the target Linux architecture:

```bash
./scripts/build-binary.sh
./dist/linux-desktop-mcp --help
```

The release binary is built on Ubuntu 22.04 (glibc baseline) and GitHub Actions smoke-tests the executable on Debian 12 and Debian 13 containers. The current prebuilt artifact targets Linux x86_64; other architectures use the uv source-install fallback. This is a CLI runtime check, not a full desktop integration test.

PyInstaller bundles the Python application and Python dependencies, but **does not bundle the desktop environment or companion services**. The target still needs the KDE/Wayland session, user D-Bus, `ydotool`, `qdbus6`, Spectacle, the KWin bridge service, and the Playwright MCP sidecar/browser. The complete desktop integration installer currently targets EndeavourOS / Arch Linux with KDE Plasma Wayland. Do not treat the standalone binary as a portable replacement for the Arch installer.

### What is installed vs. what runs

The Python CLI is the MCP server. Browser automation depends on the local Playwright MCP process on port 8931. Linux window control additionally uses the KWin D-Bus bridge in the logged-in KDE session; the Arch installer configures these sidecars as user systemd services. macOS uses its native Accessibility backend and does not use the KWin bridge. If you use only `uv tool install` or `uvx`, install and start those sidecars separately before expecting browser/window tools to work. Basic desktop tools also require their system commands and permissions.

`desktop-control-mcp status` reports Linux user services (or macOS permission guidance) and whether the local TCP endpoints are reachable. `desktop-control-mcp test` runs pytest when development dependencies are installed; for a normal uv tool install, use the development checkout and `uv sync --group dev` to run the test suite. The `linux-desktop-mcp` command remains available as a compatibility alias.


---

# macOS setup (initial native backend)

## Requirements

- macOS 13 or later
- Python 3.11+ and uv
- Node.js/npm for the Playwright MCP browser sidecar
- A logged-in interactive macOS user session

## Install from a checkout

~~~bash
git clone https://github.com/oludayoadeoye/linux-desktop-mcp.git
cd linux-desktop-mcp
uv sync --locked --group dev
npm install --global playwright-mcp playwright
playwright install firefox
~~~

Start the browser sidecar in a separate terminal:

~~~bash
playwright-mcp --port 8931 --host 127.0.0.1 --browser firefox --isolated --headless
~~~

Start the desktop MCP:

~~~bash
uv run desktop-control-mcp serve --transport http --host 127.0.0.1 --port 8932
~~~

The native macOS backend is selected automatically. The same MCP tool names and schemas are used on Linux and macOS.

## macOS privacy permissions

The first desktop interaction may trigger macOS privacy prompts. Grant:

- Accessibility to the terminal or agent host running the MCP server for mouse, keyboard, application and window operations.
- Screen Recording to the same host for desktop screenshots.

Manage these at System Settings → Privacy & Security → Accessibility and Screen Recording. Restart the MCP process after changing permissions.

## Current macOS backend scope

Quartz provides pointer and keyboard events; screencapture provides screenshots; open -a launches applications; System Events Accessibility handles window focus/minimize/maximize/restore/close. Application-specific Accessibility behavior can vary. This backend currently has mocked-Quartz unit coverage but has not yet been validated on a physical macOS host. The prebuilt one-command release installer is still Linux x86_64 only; use the uv source install on macOS.
