#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --locked --group build
uv run pyinstaller \
  --clean \
  --noconfirm \
  --onefile \
  --name linux-desktop-mcp \
  --collect-all mcp \
  --collect-all pydantic \
  --collect-submodules backends \
  cli.py
./dist/linux-desktop-mcp --help
