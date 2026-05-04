<h1 align="center">
  <img src="assets/logo.png" alt="shamefile logo" width="300">
</h1>

[![Tests](https://github.com/BKDDFS/shamefile/actions/workflows/test.yml/badge.svg)](https://github.com/BKDDFS/shamefile/actions/workflows/test.yml)
[![Lint](https://github.com/BKDDFS/shamefile/actions/workflows/lint.yml/badge.svg)](https://github.com/BKDDFS/shamefile/actions/workflows/lint.yml)
[![CodeQL](https://github.com/BKDDFS/shamefile/actions/workflows/codeql.yml/badge.svg)](https://github.com/BKDDFS/shamefile/actions/workflows/codeql.yml)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=BKDDFS_shamefile&metric=coverage)](https://sonarcloud.io/summary/new_code?id=BKDDFS_shamefile)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=BKDDFS_shamefile&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=BKDDFS_shamefile)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Rust](https://img.shields.io/badge/powered_by-Rust-b81414?logo=rust&logoColor=white)](https://www.rust-lang.org/)

> Turn linter suppressions from silent technical debt into reviewable, documented decisions.

**shamefile** is a CLI that scans your codebase for linter suppressions (`# noqa`, `// eslint-disable`, `// @ts-ignore`, and many more), consolidates them into a single registry, and fails the build until every one of them carries a written justification. Human authors and AI coding agents operate through the same interface.

## Why shamefile

A mysterious `# noqa` with no explanation, left by a developer who moved on years ago. Nobody remembers why. Nobody wants to touch it. This is how legacy code accumulates — silently, one linter suppression at a time.

`shamefile` interrupts that pattern. Every suppression is tracked in a single `shamefile.yaml` — one file, one purpose. When it changes in a pull request, a reviewer sees the full cost of a shortcut in a single diff. And as AI coding agents become routine PR authors, the registry acts as a consistent gate: whether a suppression was introduced by a human or a model, it ships with a written justification or it doesn't ship at all.

## How it works

`shamefile` exposes two stages, one command each.

**Scan** — `shame me .` walks your project, finds every suppression token, and syncs the central `shamefile.yaml`. New suppressions are registered with auto-filled metadata (owner from `git blame`, timestamp, source line). Stale entries are removed. The command fails if any entry lacks a `why`.

**Document** — `shame next` shows the first undocumented suppression, with the exact source line highlighted. Provide the reason inline (`shame next "<reason>"`), or target a specific entry with `shame fix <location> <token> --why "<reason>"`.

The same interface works for a developer opening a PR and for an AI agent iterating through gaps one at a time — without having to read the full registry into context.

## Workflow

**1. Developer writes code with a suppression:**

```python
result = parse_legacy_api(raw)  # type: ignore
```

**2. Pre-commit (or manual) run surfaces the gap:**

```
$ shame me .
Scanning . for suppressions...
Added 1 new entries to /home/user/myproject/shamefile.yaml
1 suppressions need documentation (why).
Run `shame next` to see the first one, or `shame next "<reason>"` to fill its why.

...
```

**3. Developer documents it — one entry at a time:**

```
$ shame next
./src/api.py:42
    |
  42| result = parse_legacy_api(raw)  # type: ignore

Fix with:
  shame next "<reason>"
  shame fix "./src/api.py:42" "# type: ignore" --why "<reason>"

$ shame next "legacy API returns untyped dict; types module in progress"
Documented: # type: ignore at ./src/api.py:42
All entries documented. No shame today!
```

**4. Developer commits both `api.py` and `shamefile.yaml`.** The shortcut and its justification land in the same PR, reviewable in a single diff.

## CI/CD integration

On the CI side, `shame me . --dry-run` is read-only and deterministic. It validates three contracts:

| Check | Meaning |
|---|---|
| Coverage | Every suppression in code is registered in `shamefile.yaml` |
| Staleness | Every registered entry still points at a live suppression in code |
| Justification | Every entry has a non-empty `why` |

A failure on any of the three exits non-zero.

```yaml
# .github/workflows/ci.yml
- name: Check suppressions
  run: shame me . --dry-run
```

| Flag | Description |
|---|---|
| `--dry-run` (`-n`) | Read-only validation for CI/CD — never writes to disk |
| `--hidden` | Also scan hidden files and directories (dotfiles) |

## Registry format

`shamefile.yaml` lives at the project root (git root if available, otherwise the working directory). Every entry is human-readable and stable under `git diff`:

```yaml
---
config: {}
entries:

- location: ./src/api.py:42
  token: '# type: ignore'
  content: 'result = parse_legacy_api(raw)  # type: ignore'
  created_at: 2026-04-17T21:15:05Z
  owner: Anna Nowak <anna@example.com>
  why: 'legacy API returns untyped dict; types module in progress'
```

- `location` and `token` form the entry's identity.
- `content` is the verbatim source line — used for reconciliation when code moves.
- `owner` and `created_at` are populated automatically on first run via `git blame`.
- `why` is the only field that requires a written justification — from a developer or an AI agent. The PR reviewer decides whether the reason is good enough.

## Cascade matching

A registry that breaks every time you refactor is worse than no registry. `shamefile` reconciles entries against source code in two passes:

1. **Location match** — exact `file:line` + token.
2. **Content match** — same source line + token (handles line shifts, with rename detection limited to the most recent commit via `git diff HEAD~1..HEAD -M`).

Reformatting a function or inserting imports above a suppression preserves the entry — `owner`, `created_at`, and `why` stay intact. Entries are only removed when the token itself is gone from the code.

## Supported tokens

| Token | Tool | Language |
|---|---|---|
| `# noqa` | Flake8 / Ruff | Python |
| `# pylint: disable` | Pylint | Python |
| `# type: ignore` | Mypy | Python |
| `# pyright: ignore` | Pyright | Python |
| `# pytype: disable` | Pytype | Python |
| `# pyre-ignore` / `# pyre-fixme` | Pyre | Python |
| `nosec` | Bandit | Python |
| `# pragma: no cover` | Coverage.py | Python |
| `# fmt: off` / `# fmt: skip` | Black / Ruff | Python |
| `# isort: skip` | isort | Python |
| `# lint-fixme` / `# lint-ignore` | Fixit | Python |
| `# autopep8: off` | autopep8 | Python |
| `// eslint-disable`, `/* eslint-disable` | ESLint | JS / TS / TSX |
| `// tslint:disable`, `/* tslint:disable` | TSLint | TS / TSX |
| `// @ts-ignore`, `/* @ts-ignore` | TypeScript | JS / TS / TSX |
| `// @ts-expect-error`, `/* @ts-expect-error` | TypeScript | JS / TS / TSX |

### Experimental tokens

New languages added via the [*Add a language*](.github/ISSUE_TEMPLATE/language_request.md)
template land here first. They have passed the existing test suite and
a sanity run on a real codebase, but no real-world showcase has been
contributed yet. Promotion to *Supported tokens* happens through the
[*Verify and release a language*](.github/ISSUE_TEMPLATE/showcase_request.md) flow.

| Language |
|---|
| |

Supported file extensions: `.py`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`.

## Installation

| Source | Command |
|---|---|
| **npm** | `npm install -g shamefile` |
| **PyPI** | `pip install shamefile` |
| **crates.io** | `cargo install shamefile` |
| **From source** | `cargo install --git https://github.com/BKDDFS/shamefile` |
| **Homebrew** | _coming soon_ |

All channels install the `shame` CLI. Run `shame --help` to verify.

Or as a [pre-commit](https://pre-commit.com) hook:

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/BKDDFS/shamefile
  rev: main
  hooks:
    - id: shamefile
```

## Roadmap

- **MCP server** — native integration for LLM-based PR authors (avoids loading the full registry into agent context)
- **Custom git merge driver** — auto-resolve `shamefile.yaml` conflicts on parallel PRs
- **Additional language grammars** — Rust, Go, Java, Kotlin, C# via tree-sitter
- **Custom entry fields** — attach `ticket`, `reviewer`, or `deadline` metadata to suppressions

## Contributing

Contributions are welcome. Where you start depends on what you have:

- **Found a bug?** [Open an issue](https://github.com/BKDDFS/shamefile/issues/new/choose) with a minimal repro.
- **Idea or design question?** Open a [Discussion under Ideas](https://github.com/BKDDFS/shamefile/discussions/categories/ideas) so direction can be agreed before any code is written.
- **Usage question or trouble setting things up?** Ask in [Q&A](https://github.com/BKDDFS/shamefile/discussions/categories/q-a).
- **Want to send a PR?** Read [CONTRIBUTING.md](CONTRIBUTING.md) first — dev setup, build/test/lint commands, commit format.
- **Security vulnerability?** Use the private [advisory form](https://github.com/BKDDFS/shamefile/security/advisories/new) — see [SECURITY.md](SECURITY.md). **Do not** open a public issue.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
