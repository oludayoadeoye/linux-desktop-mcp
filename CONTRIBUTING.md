# Contributing to Desktop Control MCP

Thanks for helping improve Desktop Control MCP. The goal is a small, reliable, cross-platform MCP server that is understandable and safe to maintain—not a framework that grows through unrelated abstractions.

Before changing code, read this guide and [`AGENTS.md`](AGENTS.md). If your change affects a platform backend, read the relevant backend and its tests first.

## What makes a good contribution?

Good contributions are focused, reproducible, tested, and documented. Bug fixes, missing tests, platform compatibility fixes, security improvements, and clear documentation are especially welcome. For substantial features or architectural changes, open an issue or discussion first so the design can be agreed before implementation.

## Development setup

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/oludayoadeoye/linux-desktop-mcp.git
cd linux-desktop-mcp
uv sync --locked --group dev
uv run ruff check .
uv run pytest -q
```

Run the same checks after making changes:

```bash
uv run ruff check .
uv run pytest -q
git diff --check
```

Do not report a check as passing unless you ran it and saw a successful exit code. If a platform-only test cannot run on your machine, say so explicitly and describe the alternative validation performed.

## Architecture and boundaries

Keep the current architecture unless an approved issue requires a deliberate change:

- `main.py` owns MCP tool registration, input validation, and orchestration. Keep OS-specific implementation out of this file.
- `backends/base.py` defines the platform-neutral `DesktopBackend` contract.
- `backends/linux.py`, `backends/windows.py`, and `backends/macos.py` implement that contract for their respective systems.
- `backends/__init__.py` selects the backend for the current platform.
- `cli.py` owns command-line parsing and process startup.
- `tests/` contains automated tests. Tests should not require a real desktop unless explicitly marked and isolated as an integration test.
- `scripts/`, `docs/`, and `.github/` contain installer/build workflows, user documentation, and CI/community configuration.

### Backend contract rules

- If a user-visible desktop capability is added or changed, consider whether it belongs in the shared backend protocol and whether all three backends need an implementation.
- Keep tool names, argument meaning, validation, and return semantics consistent across operating systems.
- Do not silently implement a fake success for an unsupported platform. Return a clear, actionable unsupported-operation error.
- Do not import Linux-only libraries at module import time in shared code or in a way that breaks Windows/macOS imports. Keep platform-specific imports inside the relevant backend or guarded code paths.
- Keep application launching allowlisted. Never replace an allowlist with arbitrary shell execution or pass untrusted input to a shell.
- Validate external input at the MCP boundary and again where a backend needs platform-specific constraints.
- Avoid breaking existing MCP tool names or schemas. If a breaking change is unavoidable, discuss it first and document migration/release impact.

## Implementation rules

1. **One issue, one focused change.** Do not bundle formatting, refactoring, dependency updates, and unrelated bug fixes into one pull request.
2. **Read before rewriting.** Inspect callers, tests, platform implementations, and documentation before changing an interface.
3. **Prefer the smallest clear solution.** Avoid speculative abstractions, generic plugin systems, unnecessary configuration, and premature optimization.
4. **Preserve compatibility.** Do not remove or rename public CLI commands, MCP tools, configuration options, or release assets without an approved migration plan.
5. **Keep side effects explicit.** Desktop actions can affect real user data. Never add destructive actions, broad filesystem access, hidden persistence, or network exposure without a clear security review and user-facing documentation.
6. **Use safe subprocesses.** Prefer argument arrays with `subprocess.run`/`Popen`; do not use `shell=True` for user-controlled values. Apply timeouts and check return codes where appropriate.
7. **Handle failures honestly.** Surface actionable errors. Never claim an operation succeeded if the OS or command did not confirm it.
8. **Keep dependencies lean.** Use the standard library where practical. A new runtime dependency needs a concrete reason, platform markers where appropriate, and a lockfile update using uv.
9. **Do not commit generated noise.** Do not add virtual environments, caches, local recordings, screenshots, temporary files, build output, or machine-specific configuration unless the issue explicitly calls for a reviewed release artifact.
10. **Do not change user or machine settings** as part of development or tests. Tests must mock desktop commands and APIs by default.

## Tests required

- Add or update tests for every behavior change, including validation and error paths.
- For shared MCP tools, keep the registered tool contract covered by tests; update the expected tool set when a tool is intentionally added or removed.
- For backend changes, add unit tests with mocked OS APIs/commands. Cover normal behavior, failure behavior, and unsupported/missing dependencies.
- For bug fixes, add a regression test that fails before the fix and passes after it.
- For a new backend capability, test the contract on every backend where it is supported. Clearly document any backend that does not support it yet.
- Do not make ordinary unit tests depend on an active desktop, display server, user session, browser, network service, or physical hardware.
- If real-machine testing is needed, keep it separate and document the OS, version, desktop/session, and exact manual steps.

## Documentation and release discipline

- Update README or `docs/` when behavior, installation, permissions, supported platforms, CLI usage, or troubleshooting changes.
- Keep platform support claims evidence-based: CI/unit tests are not proof of physical desktop validation. State what was actually tested and where.
- Update `uv.lock` when dependencies change. Do not hand-edit lockfile resolution data.
- Do not edit release binaries, checksums, generated metadata, or version numbers as part of an ordinary feature PR. Release preparation is a separate maintainer-led change.
- Never commit secrets, access tokens, private user data, or real desktop screenshots/recordings without explicit approval and review.

## Pull request process

1. Search existing issues and pull requests. For a significant feature or design change, discuss the approach before coding.
2. Create a focused branch from the current default branch, for example `fix/linux-mouse-coordinates` or `docs/contributing-guide`.
3. Make the smallest coherent change and add tests/documentation.
4. Run `uv run ruff check .`, `uv run pytest -q`, and `git diff --check`.
5. Review `git diff` yourself. Remove unrelated edits and generated files.
6. Open a pull request using the repository template. Explain the problem, solution, scope, tests, and platform validation.
7. Respond to review feedback with focused commits. Do not force-push or rewrite shared history unless the maintainer asks.

A pull request may be asked to change or may be closed if it is too broad, lacks tests, changes public behavior without discussion, or makes claims that are not supported by evidence.

## Commit messages

Use short, imperative messages with a clear scope, for example:

- `fix(linux): scale absolute mouse coordinates`
- `test(backends): cover unsupported window action`
- `docs: clarify macOS permission requirements`

## Reporting bugs

Include the operating system and version, desktop environment/session where relevant, Python or binary version, exact command/tool arguments (redact secrets), expected result, actual result, and reproducible steps. Include logs only after removing personal data and tokens.

## AI-assisted contributions

AI tools are welcome as assistants, not as maintainers. The human submitting a contribution is responsible for understanding, testing, and supporting every changed line. Automated agents must follow [`AGENTS.md`](AGENTS.md) in addition to this guide.
