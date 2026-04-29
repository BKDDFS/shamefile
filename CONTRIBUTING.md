# Contributing to shamefile

Thanks for taking the time to look. Contributions are welcome,
but please read this first so your time isn't wasted.

## Before you write code

- **Bugs:** open an [issue](https://github.com/BKDDFS/shamefile/issues)
  with a minimal repro.
- **Features and design questions:** open a
  [Discussion](https://github.com/BKDDFS/shamefile/discussions) under
  *Ideas*. Direction is decided there before any code is written.
- **Already-accepted work:** look for issues labeled `enhancement` or
  `bug`.

For non-trivial changes, please get agreement on the approach in the
issue or discussion before opening a PR.

## Development setup

Requirements:

- Rust **1.95.0** (matching CI)
- Python **3.14** for integration tests
- [`uv`](https://docs.astral.sh/uv/) for managing Python dependencies
- [`pre-commit`](https://pre-commit.com/) (recommended)

Clone and install hooks:

```sh
git clone https://github.com/BKDDFS/shamefile.git
cd shamefile
uv sync --all-extras
pre-commit install
```

## Build and test

```sh
cargo build              # build the binary
cargo test               # Rust unit tests
uv run pytest .     # Python tests
```

Run all three before opening a PR. CI runs the full suite on Linux,
macOS, and Windows.

## Lint and format

```sh
cargo fmt --all
cargo clippy --all-targets --all-features -- -D warnings
uv run ruff check .
uv run ruff format .
```

`pre-commit` runs all of these automatically. CI fails on any warning.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/), enforced
by the `commit-msg` hook and the PR title check:

- `feat: ...` — new user-visible behavior
- `fix: ...` — bug fix
- `docs: ...` — documentation only
- `test: ...` — tests only
- `refactor: ...` — internal change, no user-visible effect
- `chore: ...` — tooling, dependencies, release plumbing
- `ci: ...` — CI configuration

Optional scope: `feat(scanner): ...`. Use the imperative mood ("add X",
not "added X").

## Pull requests

- One logical change per PR.
- PR title follows Conventional Commits (the same rule as commit
  messages — checked by CI).
- Link the issue you're closing: `Closes #123` in the PR description.
- Keep the diff focused. Drive-by refactors go in their own PR.
- Update tests. New behavior without tests is unlikely to land.
- Update docs if user-visible behavior changes.

## Scope

shamefile detects linter suppressions, demands a written justification,
and gates on CI. The core loop is intentionally narrow.

That said, ideas outside the current scope are welcome — please raise
them in a [Discussion](https://github.com/BKDDFS/shamefile/discussions)
under *Ideas* before writing code, so direction can be agreed on first.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By
participating, you are expected to uphold it. Report unacceptable
behavior to bartekdawidflis@gmail.com.

## License

By contributing, you agree your contributions are licensed under the
Apache License 2.0 (see [LICENSE](LICENSE)).
