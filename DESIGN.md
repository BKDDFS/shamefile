# shame - Implementation Design

A tool for enforcing documentation of code suppressions.

**Philosophy**: Make technical debt management visible and enforced.

---

## Core Concept

Every code suppression (`# noqa`, `@ts-ignore`, `// eslint-disable`, etc.) must be:
1. **Registered** in a central `shamefile.yaml`
2. **Justified** with a human-readable reason

---

## Command Structure

### Single Command: `shame me`

```bash
shame me [PATH] [--dry-run]
```

**Default behavior** (local development):
- Scan code for suppressions
- **Add** new suppressions to registry (with empty why)
- **Remove** stale entries from registry (no longer in code)
- **Validate** all entries have reasons (why)
- **Save** registry to disk
- **Block** if missing reasons

**With `--dry-run`** (CI/CD):
- Scan code for suppressions
- **Check** all suppressions are registered (don't add, just report)
- **Check** no stale entries exist (don't remove, just report)
- **Check** all have reasons (why)
- **Never save** (read-only validation)
- **Fail** on any discrepancy

---

## 3-Step Validation (--dry-run mode)

### Step 1: Scan Code
```
Scanning for suppressions...
Found 42 suppressions in code
```

### Step 2: Coverage Check (Code ⊆ Registry)
```
Checking coverage (code -> shamefile)...
OK: All code suppressions are registered
```
**OR**
```
FAIL: Found 2 undocumented suppressions:
  - @ts-ignore at src/app.ts:42
  - # noqa at src/utils.py:101
```

### Step 3: Stale Check (Registry ⊆ Code)
```
Checking for stale entries (shamefile -> code)...
OK: No stale entries
```
**OR**
```
FAIL: Found 1 stale entry:
  - # noqa at src/old.py:50 (not in code anymore)
```

### Step 4: Reason Check (Why?)
```
Checking reasons...
OK: All entries have reasons
```
**OR**
```
FAIL: Found 3 entries without reason (why):
  - @ts-ignore at src/types.ts:15
  - # noqa at src/config.py:88
```

**Result**: FAIL if ANY step finds issues

---

## Registry Format (shamefile.yaml)

```yaml
config: {}

entries:
  - file: src/app.py
    line: 42
    token: "# noqa"
    author: "John Doe <john@example.com>"
    created_at: 2024-01-15T10:30:00Z
    why: "Legacy API doesn't have proper types, migration planned for Q2"

  - file: src/utils.ts
    line: 128
    token: "// @ts-ignore"
    author: "Jane Smith <jane@example.com>"
    created_at: 2024-01-20T14:22:00Z
    why: "Third-party library has incorrect type definitions, reported in issue #123"
```

### Entry Fields
| Field | Required | Description |
|-------|----------|-------------|
| `file` | Yes | Relative path from repo root |
| `line` | Yes | Line number where suppression appears |
| `token` | Yes | Exact token matched (e.g., "# noqa") |
| `author` | Yes | Git user (auto-populated) |
| `created_at` | Yes | Timestamp (auto-populated) |
| `why` | Yes | **Human-readable reason** (developer must provide) |

---

## Tracked Suppression Tokens

Defined in `src/tokens.rs`:

```rust
pub const TRACKED_TOKENS: &[&str] = &[
    "# noqa",
    "# NOSONAR",
    "# pragma: no cover",
    "// pylint: disable",
    "// eslint-disable",
    "// tslint:disable",
    "// @ts-ignore",
    "// @ts-expect-error",
];
```

**Adding new tokens**: Update `TRACKED_TOKENS` array

### Optimizations (if needed for >100K suppressions)
1. **HashSet for lookups** - O(1) instead of O(N)
2. **Streaming comparison** - Don't store all violations
3. **Incremental scanning** - Only scan changed files (git diff)
4. **Database backend** - SQLite instead of YAML

**Current decision**: Start simple, optimize only if needed

---

## Workflow Examples

### Local Development

```bash
# Developer adds a suppression
vim src/app.py
# adds: result = foo()  # noqa

# Pre-commit hook runs
git add src/app.py
git commit -m "fix bug"

# shame detects new suppression
shame me

New suppression detected: # noqa at src/app.py:42
Missing reason (why): # noqa at src/app.py:42

Validation failed! Please add reasons (why) to shamefile.yaml

exit code: 1

# Developer adds justification
vim shamefile.yaml
# justification: "False positive - linter bug #123"

# Commit again
git add shamefile.yaml
git commit -m "fix bug"

# Now passes
shame me

Validation passed. No shame today!
```

### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
- name: Check suppressions
  run: shame me --dry-run
```

```bash
# If out of sync:
shame me --dry-run

Step 1: Scanning code...
Step 2: Coverage check... FAIL: 1 undocumented
Step 3: Stale check... FAIL: 2 stale entries
Step 4: Justifications... OK

Validation failed! Run `shame me` locally to sync.

exit code: 1
```

---

## Why This Design?

### 1. Single Command = Simple Mental Model
- `shame me` = "sync everything"
- `--dry-run` = "check only"
- No confusion between `check` vs `clean`

### 2. Strict Validation = Quality
- Multi-step validation catches everything
- No half-measures (stale entries = FAIL)
- Forces discipline

---

## Future Enhancements (v2+)

### Content Hash Matching (from antigravity plan)
- Match by code content hash instead of line number
- More resilient to code movement
- Requires more complex implementation

### Per-Token Penalties
```yaml
config:
  penalties:
    "# noqa": 1
    "@ts-ignore": 2
    "eslint-disable": 3
```

### Incremental Scanning
```bash
shame me --incremental  # Only scan git-changed files
```

### Database Backend
```bash
shame me --db sqlite  # For mega-scale repos (>100K suppressions)
```


---

## Technical Architecture

### Core Modules
- **main.rs**: CLI entry point, command routing
- **scanner.rs**: Fast file scanning using `grep` crate
- **registry.rs**: YAML serialization/deserialization
- **tokens.rs**: Tracked suppression token definitions
- **git.rs**: Git user extraction for author field
- **error.rs**: Custom error types

### Key Dependencies
- `clap`: CLI argument parsing
- `grep`: Fast ripgrep-based scanning
- `ignore`: Respect .gitignore during scanning
- `serde_yaml`: Registry file I/O
- `chrono`: Timestamp handling

### Performance
- Scan speed: grep-based streaming (100-500ms for typical repo)
- Matching: O(N*M) (can optimize to O(N) with HashSet)
- Memory: ~0.5-5 MB for typical projects

---

## Success Metrics

### Adoption
- GitHub stars (goal: 10K+ like popular linters)
- Developer community mentions
- Conference talk acceptance

### Effectiveness
- % of projects that reduce suppressions after adopting
- Developer feedback on workflow improvements

---

## Summary

**`shame`** is a suppression registry tool that:
- Enforces **documentation** of all code suppressions
- Provides **strict validation** (multi-step check)
- Supports **CI/CD** (`--dry-run` mode)

**Goal**: Make suppression documentation unavoidable and effortless.