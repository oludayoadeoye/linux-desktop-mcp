"""CLI and command-line packaging tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import cli


def test_cli_defaults_to_stdio():
    args = cli.build_parser().parse_args(["serve"])
    assert args.transport == "stdio"
    assert args.host == "127.0.0.1"
    assert args.port == 8932


def test_cli_accepts_http_alias():
    args = cli.build_parser().parse_args(["serve", "--transport", "http", "--port", "9000"])
    assert args.transport == "http"
    assert args.port == 9000


def test_stdio_command_runs_mcp(monkeypatch):
    import main

    run = MagicMock()
    monkeypatch.setattr(main.mcp, "run", run)
    assert cli.main(["serve", "--transport", "stdio"]) == 0
    run.assert_called_once_with(transport="stdio")


def test_http_command_sets_host_and_port(monkeypatch):
    import main

    run = MagicMock()
    monkeypatch.setattr(main.mcp, "run", run)
    assert cli.main(["serve", "--transport", "http", "--host", "127.0.0.1", "--port", "9001"]) == 0
    assert main.mcp.settings.host == "127.0.0.1"
    assert main.mcp.settings.port == 9001
    run.assert_called_once_with(transport="streamable-http")


def test_http_rejects_invalid_port(capsys):
    assert cli.main(["serve", "--transport", "http", "--port", "70000"]) == 2
    assert "Port must be" in capsys.readouterr().err


def test_status_reports_services_and_ports(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_service_status", lambda name: "active")
    monkeypatch.setattr(cli, "_port_status", lambda port: "reachable")
    assert cli.main(["status"]) == 0
    output = capsys.readouterr().out
    assert "desktop-control.service: active" in output
    assert "Playwright MCP (127.0.0.1:8931): reachable" in output
