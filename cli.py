"""Command-line entry point for Linux Desktop MCP."""

from __future__ import annotations

import argparse
import shutil
import socket
import subprocess
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="desktop-control-mcp",
        description="Cross-platform desktop automation MCP server.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Run the MCP server.")
    serve.add_argument(
        "--transport",
        choices=("stdio", "http", "streamable-http"),
        default="stdio",
        help="MCP transport (default: stdio; http is an alias for streamable-http).",
    )
    serve.add_argument("--host", default="127.0.0.1", help="HTTP bind address.")
    serve.add_argument("--port", type=int, default=8932, help="HTTP port.")

    subparsers.add_parser("status", help="Show the status of the desktop MCP services.")
    subparsers.add_parser("test", help="Run the project pytest suite (requires dev dependencies).")
    return parser


def _service_status(name: str) -> str:
    systemctl = shutil.which("systemctl")
    if not systemctl:
        return "systemctl unavailable"
    result = subprocess.run(
        [systemctl, "--user", "is-active", name],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    return result.stdout.strip() or result.stderr.strip() or "unknown"


def _port_status(port: int) -> str:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return "reachable"
    except OSError:
        return "not reachable"


def run_status() -> int:
    print("Desktop Control MCP service status")
    if sys.platform == "darwin":
        print("Native macOS backend: selected")
        print("Accessibility permission: required for mouse, keyboard and window control")
        print("Screen Recording permission: required for screenshots")
    else:
        for service in (
            "desktop-control.service",
            "playwright-mcp.service",
            "kwin-desktop-bridge.service",
        ):
            print(f"{service}: {_service_status(service)}")
    print(f"Playwright MCP (127.0.0.1:8931): {_port_status(8931)}")
    print(f"Desktop MCP HTTP (127.0.0.1:8932): {_port_status(8932)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "status":
        return run_status()

    if args.command == "test":
        pytest = shutil.which("pytest")
        if not pytest:
            print(
                "pytest is not installed in this environment. Install development dependencies "
                "with uv sync --group dev, then run linux-desktop-mcp test.",
                file=sys.stderr,
            )
            return 2
        return subprocess.run([pytest, "-q"], check=False).returncode

    if args.command == "serve":
        from main import mcp

        transport = "streamable-http" if args.transport in ("http", "streamable-http") else "stdio"
        if transport == "streamable-http":
            if not 1 <= args.port <= 65535:
                print("Port must be between 1 and 65535.", file=sys.stderr)
                return 2
            mcp.settings.host = args.host
            mcp.settings.port = args.port
        mcp.run(transport=transport)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
