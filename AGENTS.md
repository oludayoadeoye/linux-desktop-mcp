# Instructions for AI coding agents

These instructions apply to automated coding agents, copilots, bots, and scripted contributors working in this repository. They supplement (and do not replace) [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Mandatory first steps

1. Read this file and `CONTRIBUTING.md` completely.
2. Inspect `git status --short --branch`. Do not overwrite, reset, stash, or discard pre-existing user changes.
3. Read the relevant implementation, its callers, tests, and documentation before editing.
4. Identify the exact user request or issue. If scope or expected behavior is ambiguous and materially affects the design, ask before implementing.
5. State a short plan internally and keep the patch limited to that plan.

## Non-negotiable maintenance rules

- **No drive-by changes:** do not reformat, rename, reorganize, or refactor unrelated files.
- **No broad rewrites:** do not replace modules, backend architecture, tool registration, or CLI design just because another design seems cleaner. Propose architectural changes separately and wait for maintainer approval.
- **No speculative features:** do not add abstractions, frameworks, configuration flags, compatibility layers, or dependencies without a demonstrated requirement.
- **No silent API changes:** preserve MCP tool names/schemas, CLI behavior, backend protocol semantics, installer behavior, and release asset naming unless explicitly authorized and migration is documented.
- **No invented validation:** never claim tests, builds, physical OS tests, or manual actions passed unless actually run and observed to complete successfully. Distinguish unit tests, CI builds, and real desktop tests.
- **No fake implementations:** do not return success for unsupported or unimplemented operations. Report a clear error instead.
- **No unsafe execution:** do not introduce `shell=True`, arbitrary command execution, unrestricted application launching, remote bind defaults, hidden telemetry, or destructive filesystem behavior.
- **No environment changes:** do not alter desktop settings, permissions, services, startup behavior, system packages, or user configuration to make tests pass. Ask the user/maintainer first if a change truly requires it.
- **No secrets or private artifacts:** never add credentials, tokens, personal paths, logs containing private data, or desktop captures without explicit approval.
- **No generated churn:** do not commit `.venv`, caches, `__pycache__`, test output, temporary files, build directories, local recordings, or generated binaries unless the task explicitly requests a release artifact.
- **No dependency drift:** do not add or upgrade dependencies casually. If necessary, explain why, use uv, update `uv.lock`, and test supported platforms.
- **No history manipulation:** do not amend, rebase, force-push, or push directly to the default branch unless explicitly authorized by the repository maintainer.

## Project-specific architecture

- `main.py`: MCP tool declarations, argument validation, and orchestration. Do not put OS-specific implementation here.
- `backends/base.py`: shared `DesktopBackend` protocol. Treat changes here as cross-platform API changes.
- `backends/linux.py`, `backends/windows.py`, `backends/macos.py`: native platform implementations. Keep imports and OS calls isolated to the relevant backend.
- `backends/__init__.py`: platform selection.
- `cli.py`: command-line interface and server startup.
- `tests/`: deterministic automated tests. Mock desktop APIs and subprocess calls; do not require a real desktop for unit tests.
- `scripts/`, `docs/`, `.github/`: install/build scripts, documentation, and automation.

When changing a shared capability, check all backends for parity. If a platform cannot support the capability, make that limitation explicit and return a useful error; do not silently degrade or pretend it worked. Preserve the application allowlist and loopback HTTP default.

## Required workflow for every task

1. Establish a clean baseline and note any pre-existing modifications.
2. Define the smallest set of files needed.
3. Implement one coherent change; avoid unrelated cleanup.
4. Add a regression test for a bug fix and behavior tests for new functionality, including failure paths.
5. Update user docs if usage, permissions, compatibility, security, or installation changes.
6. Run:

   ```bash
   uv run ruff check .
   uv run pytest -q
   git diff --check
   ```

   If dependencies are not installed, report that; do not silently install system packages or change machine configuration. Use the repository's documented `uv sync --locked --group dev` setup only when authorized by the task/environment.
7. Inspect the complete diff and status. Confirm there are no unrelated files, secrets, generated artifacts, or unexplained public API changes.
8. Report exactly what changed, commands run, results, limitations, and any platform tests not performed.

## Stop and ask before

- Changing the `DesktopBackend` protocol or any public MCP tool schema.
- Adding a runtime dependency or changing supported Python versions.
- Changing install scripts, service units, KWin bridge behavior, permissions, or network binding.
- Removing or renaming files, commands, tools, release assets, or supported platforms.
- Introducing persistent state, telemetry, remote access, privilege escalation, or destructive actions.
- Making a change that cannot be covered by deterministic tests.

## Definition of done

A task is complete only when the requested behavior is implemented, relevant tests pass (or limitations are clearly reported), documentation is accurate, the diff is focused, and no unsupported success or compatibility claims are made. A generated patch is not automatically ready to merge; a human maintainer reviews and approves it.
