<h1 align="center">
  <img src="assets/logo.png" alt="shame-file logo" width="300">
</h1>

<p align="center">
  <a href="https://github.com/BKDDFS/shame-file"><img src="https://img.shields.io/github/created-at/BKDDFS/shame-file?style=flat-square&color=b81414" alt="Created"></a>
  <a href="https://github.com/BKDDFS/shame-file/commits/main"><img src="https://img.shields.io/github/last-commit/BKDDFS/shame-file?style=flat-square&color=b81414" alt="Last Commit"></a>
  <a href="https://codecov.io/gh/BKDDFS/shame-file"><img src="https://img.shields.io/codecov/c/github/BKDDFS/shame-file?style=flat-square&color=b81414" alt="Coverage"></a>
  <a href="https://github.com/BKDDFS/shame-file/blob/main/LICENSE"><img src="https://img.shields.io/github/license/BKDDFS/shame-file?style=flat-square&color=b81414" alt="License"></a>
  <a href="https://github.com/BKDDFS/shame-file/releases/latest"><img src="https://img.shields.io/github/v/release/BKDDFS/shame-file?style=flat-square&color=b81414" alt="Latest Release"></a>
  <a href="https://www.rust-lang.org/"><img src="https://img.shields.io/badge/powered_by-Rust-b81414?style=flat-square&logo=rust&logoColor=white" alt="Rust"></a>
</p>

<p align="center">
  <b>Supported Languages:</b>&nbsp;&nbsp;
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black" alt="JavaScript">
</p>

<div align="center">

`# pylint: disable` · `# NOSONAR` · `/* eslint-disable */` · `// ReSharper disable` · `// NOLINT`

**No matter what language you use. No matter what linter you have.**

### IT SHOULD BE F*ING DOCUMENTED!

You **will** use this tool. ...or we **will** find you. :)<br>
Hunters guild: <img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/BKDDFS/shame-file">

</div>

## What is this?

**shamefile** is a CLI tool that scans your codebase for linter suppressions (like `// nolint`, `// eslint-disable`, `@SuppressWarnings`, and many more) and forces developers to document **why** each one exists.

Every suppression gets tracked in a central `shamefile.yaml` registry. No explanation? No merge.

## Motivation

We've all been there. A mysterious `// nolint` with no explanation, left by someone who quit two years ago. Nobody knows why. Nobody wants to touch it. This is how legacy code is born — silently, one `// eslint-disable` at a time.

**shamefile** breaks this cycle. Every suppression gets tracked in a single `shamefile.yaml` — a dedicated file with one purpose. When it changes in a PR, a reviewer understands it in seconds. Idiot-proof by design. And in the age of AI agents that love to slap `// nolint` on anything in their way — it acts as a muzzle. Human or machine, you justify it or it doesn't ship.

## How it works

Run one command:

```bash
shame me .
```

<p align="center">
  <img src="assets/screenshot.png" alt="shame me output" width="600">
</p>

That's it. Everything else is automatic — `shame me` scans your project for suppression tokens, adds new ones to the registry, removes stale entries that no longer exist in code, and fills in the author and timestamp. The only thing **you** have to do is **explain yourself** — fill in the `why` field:

```yaml
entries:
  - file: src/parser.rs
    line: 42
    token: "// eslint-disable"
    author: "Jan Kowalski <jan@example.com>"
    created_at: "2025-06-01T12:00:00Z"
    why: ""   # ← fill this in or shame won't let you merge
```

| Flag | Description |
|------|-------------|
| `--dry-run` (`-n`) | Read-only validation for CI/CD — never writes to disk |
| `--boring` (`-b`) | Professional output without gamification or emojis |

## Workflow

**1. You add a suppression to your code:**

```python
result = parse(raw_input)  # noqa: E501
```

**2. You run `shame me` (or it runs as a pre-commit hook):**

```bash
$ shame me .

🎮 Code Health: ████████████████████░ 987/1000 HP

✗ Found 1 new suppression:
  + # noqa at src/parser.py:42

Added to registry without reason why.

✗ Validation failed! Add justifications to shamefile.yaml
```

**3. You open `shamefile.yaml` and fill in the `why`:**

```yaml
entries:
  - file: src/parser.py
    line: 42
    token: "# noqa"
    author: "Jan Kowalski <jan@example.com>"
    created_at: "2025-06-01T12:00:00Z"
    why: "Raw input line can exceed 120 chars — truncating would break parsing"
```

**4. You commit both files. Now it passes:**

```bash
$ shame me .

🎮 Code Health: ████████████████████░ 987/1000 HP

💚 EXCELLENT! No shame today!

✓ All suppressions are documented!
```

In CI, use `--dry-run` to validate without modifying the registry:

```yaml
# .github/workflows/ci.yml
- name: Check suppressions
  run: shame me . --dry-run
```

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/BKDDFS/shame-file/main/install.sh | bash
```

Or as a [pre-commit](https://pre-commit.com) hook:

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/BKDDFS/shame-file
  rev: v0.1.0
  hooks:
    - id: shamefile
```

## Configuration

The `shamefile.yaml` config section controls tool behavior:

```yaml
config:
  max_suppressions: 1000
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_suppressions` | `1000` | Maximum number of allowed suppressions. When your codebase exceeds this limit, `shame` will block further suppressions and declare **LEGACY HELL**. Lower it over time to force cleanup. |

## Supported tokens

| Token | Tool | Language |
|-------|------|----------|
| `NOSONAR` | SonarQube / SonarCloud | Any |
| `nosemgrep` | Semgrep | Any |
| `# noqa` | Flake8 / Ruff | Python |
| `# pylint: disable` | Pylint | Python |
| `# type: ignore` | Mypy | Python |
| `# pyright: ignore` | Pyright | Python |
| `# pytype: disable` | Pytype | Python |
| `# pyre-ignore` | Pyre | Python |
| `# pyre-fixme` | Pyre | Python |
| `# nosec` | Bandit | Python |
| `# pragma: no cover` | Coverage.py | Python |
| `# fmt: off` | Black / Ruff | Python |
| `# fmt: skip` | Black / Ruff | Python |
| `# isort: skip` | isort | Python |
| `# lint-fixme` | Fixit | Python |
| `# lint-ignore` | Fixit | Python |
| `# autopep8: off` | autopep8 | Python |
| `#[allow(` | Clippy / rustc | Rust |
| `#[rustfmt::skip]` | rustfmt | Rust |
| `// eslint-disable` | ESLint | JavaScript |
| `// tslint:disable` | TSLint | JavaScript |
| `// @ts-ignore` | TypeScript | TypeScript |
| `// @ts-expect-error` | TypeScript | TypeScript |

## Contributing

**Missing a token for your linter?** [Open an issue](https://github.com/BKDDFS/shame-file/issues) first — let's agree on scope before you write code.
