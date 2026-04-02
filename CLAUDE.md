# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**shamefile** is a CLI tool that enforces documentation of code suppressions (e.g., `# noqa`, `// eslint-disable`, `// @ts-ignore`). It scans codebases for suppression tokens and maintains a central `shamefile.yaml` registry requiring justifications for each suppression. See [DESIGN.md](DESIGN.md) for the full design document.

## Build and Development

```bash
cargo build                          # Build debug binary
cargo build --release                # Build optimized release
maturin build --release              # Build Python wheel for pip distribution

cargo run -- me .                    # Run: scan current dir
cargo run -- me . --dry-run          # Run: CI validation mode (read-only)

```

### Testing

```bash
cargo test                           # All tests (unit + integration)
cargo test --lib                     # Unit tests only (in src/*.rs)
cargo test --test integration_tests  # Integration tests only
cargo test test_regex_matches_all_tokens  # Single test by name
```

Integration tests shell out to the compiled binary, so run `cargo build` before `cargo test --test integration_tests` if you've only edited source.

## Architecture

### Modules

- **main.rs** - CLI entry point (clap). Single subcommand `me` with `--dry-run` flag. Contains `handle_normal()` and `handle_dry_run()` which are the two main code paths
- **scanner.rs** - Uses `grep` crate + `ignore` crate (respects .gitignore) to find suppression tokens. Returns `Vec<Violation>` with path, line number, content, and matched token
- **registry.rs** - Manages `shamefile.yaml` via serde. Core types: `Registry` (config + entries), `Config`, `Entry` (file, line, token, author, created_at, **why**)
- **tokens.rs** - Hardcoded `TRACKED_TOKENS` array and `get_token_regex()` that builds alternation pattern. To add new tokens, update the `TRACKED_TOKENS` constant

- **git.rs** - Shells out to `git config` to get author name/email for new entries
- **error.rs** - `ShamefileError` enum using thiserror
- **lib.rs** - Public module declarations; crate name is `shamefile`

### Key Data Flow

**Normal mode** (`shame me`): Load/create registry -> scan for violations -> add new entries (with empty `why`) -> remove stale entries -> validate all `why` fields populated -> save to disk -> exit 1 if validation fails.

**Dry-run mode** (`shame me --dry-run`): Load existing registry (fail if missing) -> scan -> 3-step read-only validation (coverage check, stale check, justification check) -> never saves -> exit 1 on any failure.

### Important Details

- Entry matching between code violations and registry is by **triple**: (file path, line number, token)
- The justification field is named **`why`** (not "justification") in both code and YAML
- Scanner finds which token matched by iterating `TRACKED_TOKENS` and checking `line.contains(t)` after the regex already confirmed a match
- `shamefile.yaml` is always created in the scanned directory (`scan_path.join("shamefile.yaml")`)
- Binary exits via `std::process::exit(1)` on failures, not error propagation

### Testing Notes

- Integration tests use `tests/fixtures/sample.py` and `tests/fixtures/sample.js` as fixture files
- Tests create isolated temp dirs via `tempfile` crate, copying fixtures in
- Binary path for integration tests: `target/debug/shame`

## Packaging

Distributed via pip (`pip install shamefile`) using maturin with `bindings = "bin"` - pure Rust binary, no Python bindings.