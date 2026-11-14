#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
KWINSCRIPT_DIR="$HOME/.local/share/kwin/scripts/linux-desktop-mcp"
NPM_PREFIX="${NPM_CONFIG_PREFIX:-$HOME/.npm-global}"

if [[ ! -f /etc/arch-release && ! -f /etc/endeavouros-release ]]; then
  echo "This installer targets Arch Linux and EndeavourOS." >&2
  exit 1
fi

if ! command -v sudo >/dev/null 2>&1; then
  echo "sudo is required to install system packages." >&2
  exit 1
fi

sudo pacman -S --needed --noconfirm python python-dbus python-gobject glib2 nodejs npm git uv

UV_BIN="$(command -v uv || true)"
if [[ -z "$UV_BIN" ]]; then
  echo "uv was not found after package installation." >&2
  exit 1
fi

mkdir -p "$NPM_PREFIX" "$USER_SYSTEMD_DIR" "$KWINSCRIPT_DIR/contents/code"
npm config set prefix "$NPM_PREFIX"
export PATH="$NPM_PREFIX/bin:$HOME/.local/bin:$PATH"
npm install --global playwright-mcp playwright mcp-remote
PLAYWRIGHT_MCP_BIN="$(command -v playwright-mcp)"
PLAYWRIGHT_BIN="$(command -v playwright)"
"$PLAYWRIGHT_BIN" install firefox

cd "$PROJECT_DIR"
"$UV_BIN" sync --locked --group dev

cp "$PROJECT_DIR/kwin-plugin/metadata.json" "$KWINSCRIPT_DIR/metadata.json"
cp "$PROJECT_DIR/kwin-plugin/contents/code/main.js" "$KWINSCRIPT_DIR/contents/code/main.js"

cat > "$USER_SYSTEMD_DIR/kwin-desktop-bridge.service" <<EOF
[Unit]
Description=KWin bridge for Linux Desktop MCP
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/python $PROJECT_DIR/kwin-bridge-service.py
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
EOF

cat > "$USER_SYSTEMD_DIR/playwright-mcp.service" <<EOF
[Unit]
Description=Local Playwright MCP Browser Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$PLAYWRIGHT_MCP_BIN --port 8931 --host 127.0.0.1 --browser firefox --isolated --headless
Restart=on-failure
RestartSec=3
Environment=NODE_ENV=production

[Install]
WantedBy=default.target
EOF

cat > "$USER_SYSTEMD_DIR/desktop-control.service" <<EOF
[Unit]
Description=Local KDE Desktop Control MCP Server
After=graphical-session.target playwright-mcp.service kwin-desktop-bridge.service
Wants=playwright-mcp.service kwin-desktop-bridge.service

[Service]
Type=simple
WorkingDirectory=$PROJECT_DIR
ExecStart=$UV_BIN run --project $PROJECT_DIR --no-sync python main.py
Restart=on-failure
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
EOF

if command -v kwriteconfig6 >/dev/null 2>&1; then
  kwriteconfig6 --file kwinrc --group Plugins --key linux-desktop-mcpEnabled true
else
  echo "kwriteconfig6 is missing; enable the KWin script plugin manually." >&2
fi

systemctl --user daemon-reload
systemctl --user enable --now kwin-desktop-bridge.service playwright-mcp.service desktop-control.service

echo
echo "Installation complete. MCP endpoint: http://127.0.0.1:8932/mcp"
echo "Playwright endpoint: http://127.0.0.1:8931/mcp"
echo "Log out and back in (or restart KWin) to load the installed KWin script."
echo "Run tests with: cd '$PROJECT_DIR' && uv run pytest -q"
