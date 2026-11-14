#!/usr/bin/env bash
set -Eeuo pipefail

REPO="oludayoadeoye/linux-desktop-mcp"
ASSET_NAME=""
BIN_NAME="desktop-control-mcp"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
API_URL="https://api.github.com/repos/$REPO/releases/latest"

say() { printf '[linux-desktop-mcp] %s\n' "$*"; }
die() { printf '[linux-desktop-mcp] ERROR: %s\n' "$*" >&2; exit 1; }

command -v curl >/dev/null 2>&1 || die "curl is required."
command -v python3 >/dev/null 2>&1 || die "python3 is required to validate release metadata."
command -v sha256sum >/dev/null 2>&1 || die "sha256sum is required."
[[ "$(uname -s)" == "Linux" ]] || die "This installer currently supports Linux only."

# Private repositories require a token. Prefer an explicitly supplied token,
# then fall back to the user's authenticated GitHub CLI session.
GH_TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
if [[ -z "$GH_TOKEN" ]] && command -v gh >/dev/null 2>&1; then
  GH_TOKEN="$(gh auth token 2>/dev/null || true)"
fi
CURL_AUTH=()
if [[ -n "$GH_TOKEN" ]]; then
  CURL_AUTH=(-H "Authorization: Bearer $GH_TOKEN")
fi

ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64) ASSET_NAME="desktop-control-mcp-linux-x86_64" ;;
  aarch64|arm64) ASSET_NAME="desktop-control-mcp-linux-aarch64" ;;
  *)
    say "No prebuilt Linux binary for $ARCH; using the uv source installation."
    if ! command -v uv >/dev/null 2>&1; then
      say "Installing uv using Astral's official installer..."
      curl -LsSf https://astral.sh/uv/install.sh | sh
      export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    fi
    command -v uv >/dev/null 2>&1 || die "uv installation failed. Install uv and rerun this script."
    uv tool install --upgrade "git+https://github.com/$REPO"
    say "Installed from source with uv. Ensure $HOME/.local/bin is on PATH."
    exit 0
    ;;
esac

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
curl -fsSL "${CURL_AUTH[@]}" "$API_URL" -o "$TMP_DIR/release.json" || die "Could not access the GitHub release. If the repository is private, authenticate with 'gh auth login' first."

readarray -t RELEASE_INFO < <(python3 - "$TMP_DIR/release.json" "$ASSET_NAME" <<'PY'
import json, sys
release = json.load(open(sys.argv[1], encoding="utf-8"))
asset = next((a for a in release.get("assets", []) if a.get("name") == sys.argv[2]), None)
if not asset:
    raise SystemExit("Latest release does not contain the matching Linux executable.")
digest = asset.get("digest") or ""
if not digest.startswith("sha256:"):
    raise SystemExit("GitHub release metadata has no SHA-256 digest; refusing an unverifiable download.")
print(release["tag_name"])
print(asset["browser_download_url"])
print(digest.split(":", 1)[1])
PY
) || die "Could not read verified release metadata."
[[ "${#RELEASE_INFO[@]}" -eq 3 ]] || die "Incomplete GitHub release metadata."
TAG="${RELEASE_INFO[0]}"
DOWNLOAD_URL="${RELEASE_INFO[1]}"
EXPECTED_SHA="${RELEASE_INFO[2]}"

say "Downloading $ASSET_NAME $TAG..."
if [[ -n "$GH_TOKEN" ]] && command -v gh >/dev/null 2>&1; then
  gh release download "$TAG" --repo "$REPO" --pattern "$ASSET_NAME" --dir "$TMP_DIR" --clobber
else
  curl -fL --retry 3 "$DOWNLOAD_URL" -o "$TMP_DIR/$ASSET_NAME"
fi
ACTUAL_SHA="$(sha256sum "$TMP_DIR/$ASSET_NAME" | awk '{print $1}')"
[[ "$ACTUAL_SHA" == "$EXPECTED_SHA" ]] || die "SHA-256 verification failed. The downloaded file will not be installed."

mkdir -p "$INSTALL_DIR"
install -m 0755 "$TMP_DIR/$ASSET_NAME" "$INSTALL_DIR/$BIN_NAME"
say "Installed $BIN_NAME to $INSTALL_DIR/$BIN_NAME"
"$INSTALL_DIR/$BIN_NAME" --help >/dev/null || die "Installed executable failed its smoke test."
say "Installation verified."
case ":$PATH:" in
  *":$INSTALL_DIR:"*) ;;
  *) say "Add this to your shell profile: export PATH=\"$INSTALL_DIR:\$PATH\"" ;;
esac
say "Run: $BIN_NAME serve --transport stdio"
