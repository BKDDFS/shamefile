<img src="assets/logo.png" alt="shamefile logo" width="180" align="left">

&nbsp;

**Turn silent tech debt into reviewable and documented decisions.**

[![Tests](https://github.com/BKDDFS/shamefile/actions/workflows/test.yml/badge.svg)](https://github.com/BKDDFS/shamefile/actions/workflows/test.yml)
[![Lint](https://github.com/BKDDFS/shamefile/actions/workflows/lint.yml/badge.svg)](https://github.com/BKDDFS/shamefile/actions/workflows/lint.yml)
[![CodeQL](https://github.com/BKDDFS/shamefile/actions/workflows/codeql.yml/badge.svg)](https://github.com/BKDDFS/shamefile/actions/workflows/codeql.yml)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=BKDDFS_shamefile&metric=coverage)](https://sonarcloud.io/summary/new_code?id=BKDDFS_shamefile)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=BKDDFS_shamefile&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=BKDDFS_shamefile)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Rust](https://img.shields.io/badge/powered_by-Rust-b81414?logo=rust&logoColor=white)](https://www.rust-lang.org/)
[![shamefile](https://img.shields.io/badge/tracked_with-shamefile-b81414)](https://github.com/BKDDFS/shamefile)

<br clear="left">

**shamefile** won't let anyone silence a linter warning in your code without writing down why.

People are lazy. Both committer and code reviewer.

- The **committer** slaps a `// NOLINT` comment when there's no easy fix. They don't justify it — in most languages there's no good place for that.
- The **code reviewer** focuses on more important things: security, bugs, design. There's no dedicated time for checking new suppression arrivals.

Shamefile adds `shamefile.yaml` for the code reviewer and the `shame` CLI for the committer to give them tools to react before tech debt gets out of control.

## Why it's important

A mysterious `# noqa` with no explanation, left by a developer who moved on years ago. Nobody remembers why. Nobody wants to touch it. This is how legacy code accumulates — silently, one linter suppression at a time.

`shamefile` interrupts that pattern. Every suppression is tracked in a single `shamefile.yaml` — one file, one purpose. When it changes in a pull request, a reviewer sees the full cost of a shortcut in a single diff. And as AI coding agents become routine PR authors, the registry acts as a consistent gate: whether a suppression was introduced by a human or a model, it ships with a written justification or it doesn't ship at all.

## How it works

`shamefile` exposes two stages, one command each.

**Scan** — `shame me .` walks your project, finds every suppression token, and syncs the central `shamefile.yaml`. New suppressions are registered with auto-filled metadata (owner from `git blame`, timestamp, source line). Stale entries are removed. The command fails if any entry lacks a `why`.

**Document** — `shame next` shows the first undocumented suppression, with the exact source line highlighted. Provide the reason inline (`shame next "<reason>"`), or target a specific entry with `shame fix <location> <token> --why "<reason>"`. To delete a stale entry without editing the YAML by hand, use `shame remove <location> <token>` (alias `shame rm`).

The same interface works for a developer opening a PR and for an AI agent iterating through gaps one at a time — without having to read the full registry into context.

## Workflow

**1. Developer writes code with a suppression:**

```python
result = parse_legacy_api(raw)  # type: ignore
```

**2. Pre-commit (or manual) run surfaces the gap:**

```
$ shame me .
Creating new registry at /home/user/myproject/shamefile.yaml
Scanning . for suppressions...
Added 1 new entries to /home/user/myproject/shamefile.yaml
1 suppressions need documentation (why).
Run `shame next` to see the first one, or `shame next "<reason>"` to fill its why.

...
```

**3. Developer documents it:**

```
$ shame next
./src/api.py:42
    |
  42| result = parse_legacy_api(raw)  # type: ignore
    |                                 ^^^^^^^^^^^^^^

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
  created_at: 2026-04-17
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
- **Native exclusion config** — first-class `exclude:` patterns in `shamefile.yaml` for checked-in vendored or generated code that bypasses the default `.gitignore` discovery

## FAQ

**Why not just write the reason inline, like `# noqa: F401  # legacy import`?**

- **Reviewers don't see it.** A `# noqa` buried in one of seven changed files rarely gets pushback. `shamefile.yaml` puts every suppression in the PR into one diff — the reviewer sees the full cost as a single list, with author and `why` per entry.
- **Nothing forces a reason.** Linters accept any string after the token, or none. `shame me . --dry-run` fails the build until every entry has a non-empty `why`. This matters most for AI coding agents, which lose the suppression's context the moment the session ends — the registry forces them to write the reason to disk while it still exists.
- **Inline is a bad trade-off.** A short reason carries no information; a useful one drowns the line of code it is attached to. The registry keeps source readable and justifications detailed.

**What stops developers from writing `why: 'TODO'` and moving on?**

The tool guarantees a string is written; the reviewer judges whether it is a real reason. If `why: 'TODO'` passes review, that is an organisational gap, not a tool gap — but the registry makes the gap visible: every lazy entry is one `grep` away, by author and date. Before `shamefile`, the same shortcut was hidden inside whichever file it lived in.

**Won't `shamefile.yaml` become a merge conflict magnet on parallel PRs?**

The registry is sorted by `(location, token)`, so suppressions added in unrelated parts of the codebase land in different regions of the file — most parallel PRs do not collide. When they do, `shame me` is idempotent: after a merge, running it on the resolved tree deterministically reconciles entries from source, so `git checkout --theirs shamefile.yaml && shame me .` is the escape hatch. A custom git merge driver that resolves automatically is on the Roadmap. This is the same trade-off every shared-file tool (lockfiles, changelogs, schema migrations) has accepted in exchange for single-source-of-truth visibility.

**What about generated, vendored, or third-party code?**

A repo's typical generated/vendored content is excluded for free:

- `.gitignore` and `.ignore` files are respected (handled by the same engine `ripgrep` uses), so `node_modules/`, `target/`, `dist/`, `__pycache__/` etc. are skipped without configuration.
- Only `.py / .js / .jsx / .mjs / .cjs / .ts / .tsx` are scanned, so vendored content in any other language is silently ignored.

A first-class `exclude:` config in `shamefile.yaml` is on the [Roadmap](#roadmap).

## Contributing

Contributions are welcome. Where you start depends on what you have:

- **Found a bug?** [Open an issue](https://github.com/BKDDFS/shamefile/issues/new/choose) with a minimal repro.
- **Idea or design question?** Open a [Discussion under Ideas](https://github.com/BKDDFS/shamefile/discussions/categories/ideas) so direction can be agreed before any code is written.
- **Usage question or trouble setting things up?** Ask in [Q&A](https://github.com/BKDDFS/shamefile/discussions/categories/q-a).
- **Want to send a PR?** Read [CONTRIBUTING.md](CONTRIBUTING.md) first — dev setup, build/test/lint commands, commit format.
- **Security vulnerability?** Use the private [advisory form](https://github.com/BKDDFS/shamefile/security/advisories/new) — see [SECURITY.md](SECURITY.md). **Do not** open a public issue.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
