# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**shame** is a gamified, language-agnostic CLI tool that enforces documentation of code suppressions (e.g., `# noqa`, `// eslint-disable`, `// @ts-ignore`). It scans codebases for suppression tokens and maintains a central `shamefile.yaml` registry requiring justifications for each suppression.

**Key Features:**
- Single command (`shame me`) with `--dry-run` for CI/CD
- Suppression budget system (HP bar) - configurable max suppressions
- Fun, memorable output by default (inspired by tools like `thefuck`)
- 4-step strict validation in dry-run mode
- Escape hatch (`--boring` flag) for professional environments

**Philosophy**: Make technical debt management fun, memorable, and viral-worthy.

## Build and Development

### Building

This is a Rust project packaged with maturin for distribution via pip:

```bash
# Build the Rust binary
cargo build

# Build optimized release version
cargo build --release

# Build Python wheel for distribution
maturin build --release
```

### Testing

```bash
# Run all tests (unit + integration)
cargo test

# Run only unit tests (in src/*.rs)
cargo test --lib

# Run only integration tests
cargo test --test integration_tests

# Run specific test
cargo test test_regex_matches_all_tokens
```

### Running Locally

```bash
# Run the binary directly (main command)
cargo run -- me .
cargo run -- me . --dry-run
cargo run -- me /path/to/scan --config custom.yaml

# With flags
cargo run -- me . --boring  # Professional output mode
```

## Architecture

### Core Components

- **main.rs**: CLI entry point using clap. Single command: `me` with optional `--dry-run` and `--boring` flags
- **scanner.rs**: Uses `grep` crate to search for suppression tokens across files. Respects `.gitignore` via `ignore` crate
- **registry.rs**: Manages `shamefile.yaml` file with serde. Contains `Entry` structs with metadata (file, line, token, author, created_at, justification). Also handles suppression budget/HP system
- **tokens.rs**: Defines hardcoded list of tracked suppression tokens across languages
- **git.rs**: Extracts git author info (`git config user.name` and `user.email`) for new entries
- **error.rs**: Custom error types using thiserror

### Key Data Flow

**`shame me` (normal mode - local development):**
1. Load existing `shamefile.yaml` or create new registry
2. Scan target path for all suppression tokens using regex
3. **Two-way sync**:
   - Add new suppressions found in code (with empty justification)
   - Remove stale registry entries (no longer in code)
4. Validate all entries have justifications
5. Check against suppression budget (max_suppressions)
6. **Save** registry to disk
7. Exit with code 1 if validation fails or over budget

**`shame me --dry-run` (CI/CD validation):**
1. Load existing `shamefile.yaml` (fail if doesn't exist)
2. Scan target path for all suppression tokens
3. **4-step validation** (read-only, never saves):
   - Step 1: Scan code for suppressions
   - Step 2: Check all code suppressions are in registry (fail if not)
   - Step 3: Check no stale entries in registry (fail if found)
   - Step 4: Check all entries have justifications (fail if missing)
4. Check against suppression budget
5. **Never save** - exit with code 1 if any step fails

**Key difference**: Normal mode modifies registry, dry-run mode only validates.

### Tracked Suppression Tokens

The tool currently tracks these hardcoded tokens (see `tokens.rs`):
- Python/YAML/Shell: `# noqa`, `# NOSONAR`, `# pragma: no cover`, `// pylint: disable`
- JavaScript/TypeScript: `// eslint-disable`, `// tslint:disable`, `// @ts-ignore`, `// @ts-expect-error`

When adding new tokens, update `TRACKED_TOKENS` in `tokens.rs`.

## Testing Notes

- Integration tests use fixture files in `tests/fixtures/` (sample.py, sample.js)
- Tests clean up `shamefile.yaml` before/after runs to ensure clean state
- Binary location for tests: `target/debug/shamefile`

## Configuration

The `shamefile.yaml` registry format:

```yaml
config:
  version: "0.1.0"
  max_suppressions: 1000  # Suppression budget (HP cap)

entries:
  - file: src/example.py
    line: 42
    token: "# noqa"
    author: "Name <email>"
    created_at: 2024-01-15T10:30:00Z
    justification: "Reason why this suppression is needed"
```

### Suppression Budget System (HP Bar)

- `max_suppressions`: Configurable cap on total suppressions (default: 1000)
- Each entry = -1 HP consumed
- Display: `████████████████████░ 988/1000 HP`
- At 0 HP: Block new suppressions ("LEGACY HELL")
- Gamification: Removing suppressions = +HP = motivates cleanup

### Output Modes

**Default (fun mode):**
```bash
🎮 Code Health: ████████████████████░ 988/1000 HP
💚 EXCELLENT! No shame today!
```

**Professional mode (`--boring`):**
```bash
Suppression Budget: 988/1000 (98.8%)
Status: Excellent
Validation passed
```

## Maturin Packaging

`pyproject.toml` configures maturin to build a pure binary (no Python bindings):
- `bindings = "bin"`: Build as CLI tool, not Python library
- Distributed via `pip install shame`
- Rust binary is the entire implementation; Python is only for packaging

## Design Philosophy

**See [DESIGN.md](DESIGN.md) for complete design document.**

Key principles:
1. **Single command**: `shame me [--dry-run]` - simple mental model
2. **Gamification**: HP bar makes technical debt visible and fun to manage
3. **Personality by default**: Fun, memorable output (inspired by `thefuck`)
4. **Strict validation**: 4-step check in dry-run mode catches everything
5. **Escape hatch**: `--boring` flag for professional environments
6. **Viral-worthy**: Make it shareable, memorable, conference-talk material

**Goal**: Be the `thefuck` of linter enforcement - useful, memorable, and viral.
