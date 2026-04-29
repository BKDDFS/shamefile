---
name: Add a language
about: Track adding support for a new language. Tick boxes as you go.
title: "lang: add support for <language>"
labels: ["enhancement", "language"]
---

Adding a language to shamefile is mechanical. Tick each box as you
complete it, then link the PR with `Closes #<this-issue>`.

> **One language per contributor.** Adding a language is a well-scoped
> first contribution and we keep this opportunity open for new
> contributors. If you have already had a language PR merged, please do
> not open another one.

## Language

- Name:
- File extensions:
- Tree-sitter grammar:

## Pre-flight checks

Before opening a PR, confirm the language is implementable. If either of
these fails, **do not** open a PR — comment on this issue with your
findings so a maintainer can decide whether to keep it open or close it.

- [ ] **A `tree-sitter-<lang>` Rust crate is published on crates.io.**
  Search [crates.io](https://crates.io/search?q=tree-sitter-) for the
  crate. The crate must:
  - export a `LANGUAGE` constant (or equivalent function) usable from
    Rust;
  - declare a `tree-sitter` dependency compatible with the version
    pinned in [`Cargo.toml`](../blob/main/Cargo.toml).

  A grammar that exists only as a C / JavaScript repo (no Rust binding
  on crates.io) does **not** qualify. Adding bindings is a separate,
  much larger contribution and is out of scope for this template.

- [ ] **The language has at least one inline suppression token** used in
  practice (linter, type checker, formatter, compiler attribute, IDE
  inspection, security scanner, coverage tool, or cross-language SaaS).
  shamefile is built around inline suppressions; languages with no
  inline suppression mechanism are not in scope. The existing test
  suite enforces this (`every_language_has_tokens` in
  [`src/languages.rs`](../blob/main/src/languages.rs)).

## Checklist

- [ ] Add the `tree-sitter-<lang>` dependency to [`Cargo.toml`](../blob/main/Cargo.toml).
- [ ] Add a `Language` entry to [`src/languages.rs`](../blob/main/src/languages.rs) under `LANGUAGES`:
  - [ ] `name`
  - [ ] `extensions` (no leading dot)
  - [ ] `tokens` — suppression tokens used by the language's ecosystem. Cover every category that applies; not all languages have all of these.
    - [ ] every token has a trailing `// <tool>` comment naming the linter, type checker, formatter, or other tool the token comes from (matches the convention in existing entries)
    - [ ] **Linters and type checkers** native to the language (e.g. ruff, mypy, eslint, clippy, golangci-lint).
    - [ ] **Formatters** with inline disables (e.g. `# fmt: off` for Black/Ruff, `// prettier-ignore`).
    - [ ] **Compiler / language built-in suppression attributes** — often the most widespread:
      - Rust: `#[allow(...)]`, `#[expect(...)]`
      - Java: `@SuppressWarnings("...")`
      - C#: `#pragma warning disable`, `[SuppressMessage(...)]`
      - Kotlin: `@Suppress("...")`
      - C / C++: `#pragma GCC diagnostic ignored`, `#pragma clang diagnostic ignored`, `#pragma warning(disable: ...)` (MSVC)
    - [ ] **JetBrains IDE inspection** — works in IntelliJ / PyCharm / WebStorm / Rider / GoLand and is easy to miss: `// noinspection`, `# noinspection`.
    - [ ] **Per-language security scanners** — e.g. Bandit (`# nosec`), gosec (`// #nosec`), Brakeman (`# brakeman:ignore`).
    - [ ] **Per-language coverage tools** — e.g. coverage.py (`# pragma: no cover`), istanbul / c8 (`/* istanbul ignore */`), tarpaulin (Rust), SimpleCov (Ruby).
    - [ ] **Cross-language tools** with inline suppression — each tool's comment prefix differs per language; they are NOT handled universally. Examples to research: SonarQube / SonarLint (`NOSONAR`), DeepSource (`skipcq`), SemGrep (`nosemgrep`), Snyk Code (`deepcode ignore`), Coverity (`coverity[...]`).
  - [ ] `grammar` — closure returning the tree-sitter language
  - [ ] `comment_types` — tree-sitter node names treated as comments. The default in existing entries is `["comment"]`, but many grammars expose `line_comment` and `block_comment` as separate node types instead. Verify by one of:
    - Reading the grammar's `node-types.json` (shipped in most published crates) and listing every node whose name contains `comment`.
    - Reading the grammar's `grammar.js` source and looking at the `$.comment` / `$.line_comment` rules.
    - Writing a throwaway test that parses a small sample (one line comment, one block comment if applicable) and prints `node.kind()` for every node — adjust `comment_types` until both styles are covered.
- [ ] All file extensions for the language are covered, including edge cases:
  - [ ] Stub / declaration files (e.g. `.pyi` for Python, `.d.ts` for TypeScript).
  - [ ] Multi-language container files (e.g. `.vue`, `.svelte`) — call out in the PR if they are out of scope, since they need additional handling.
  - [ ] Shebang-only scripts without an extension are out of scope. For languages where shebang-only is the dominant pattern (e.g. shell scripts), this is a **partial** language addition — proceed only if a meaningful share of real-world code uses an extension, and clearly document the limitation in the PR description.
- [ ] Tests in `src/languages.rs`:
  - [ ] `<lang>_found_by_extension`
  - [ ] One assertion confirming a representative suppression token is recognized
  - [ ] One assertion confirming a foreign token is NOT recognized
- [ ] `cargo test` passes locally.
- [ ] `cargo clippy --all-targets --all-features -- -D warnings` passes.
- [ ] **Sanity check on a real codebase** — exercise the new language end-to-end against unfamiliar code. Steps:
  1. Build a release binary with your changes:
     ```sh
     cargo build --release
     ```
  2. Clone a representative open-source project written in this language somewhere **outside this repo**:
     ```sh
     git clone --depth=1 https://github.com/<org>/<repo> /tmp/sanity
     ```
  3. Run shame in normal (write) mode against it. This generates a `shamefile.yaml` inside `/tmp/sanity` — a local-only file you will throw away, do **not** commit or push it back to that project:
     ```sh
     ./target/release/shame me /tmp/sanity
     ```
  4. Open the generated `/tmp/sanity/shamefile.yaml` and spot-check entries:
     - Real suppressions, not false positives.
     - `location`, `token`, and metadata look right.
     - Output is well-formed YAML and renders cleanly in `git diff`.
  5. Run `--dry-run` mode (CI path) and confirm it agrees with the saved registry:
     ```sh
     ./target/release/shame me --dry-run /tmp/sanity
     ```
  6. In the PR description, include: the project URL, its commit SHA, the suppression count, and any anomalies.

  > **Please do not open a PR against the upstream project** introducing
  > `shamefile.yaml` to their repo as part of testing. If you think a
  > project would benefit from shamefile, open an issue in **their**
  > tracker first asking whether they want it. Unsolicited setup PRs
  > are noise for maintainers.
- [ ] [README](../blob/main/README.md) updated with the new language. Specifically:
  - Add a row per token to the **Supported tokens** table, matching the format of the existing Python / JavaScript / TypeScript rows (token in backticks, source tool, language column with the new language name).
  - Add the file extension(s) to the **Supported file extensions** list.
  - Keep alphabetical / logical grouping consistent with existing entries.

## Notes

(edge cases, tooling overlap, anything maintainers should know)
