# shame - Implementation Design

A gamified tool for enforcing documentation of code suppressions.

**Philosophy**: Make technical debt management fun, memorable, and viral-worthy.

---

## Core Concept

Every code suppression (`# noqa`, `@ts-ignore`, `// eslint-disable`, etc.) must be:
1. **Registered** in a central `shamefile.yaml`
2. **Justified** with a human-readable reason
3. **Within budget** (configurable suppression cap)

---

## Command Structure

### Single Command: `shame me`

```bash
shame me [PATH] [--dry-run] [--boring]
```

**Default behavior** (local development):
- Scan code for suppressions
- **Add** new suppressions to registry (with empty justification)
- **Remove** stale entries from registry (no longer in code)
- **Validate** all entries have justifications
- **Save** registry to disk
- **Block** if over budget or missing justifications

**With `--dry-run`** (CI/CD):
- Scan code for suppressions
- **Check** all suppressions are registered (don't add, just report)
- **Check** no stale entries exist (don't remove, just report)
- **Check** all have justifications
- **Never save** (read-only validation)
- **Fail** on any discrepancy

**With `--boring`** (optional):
- Professional output (no emojis, minimal flair)
- For corporate environments

---

## 4-Step Validation (--dry-run mode)

### Step 1: Scan Code
```
Scanning for suppressions...
Found 1001 suppressions in code
```

### Step 2: Coverage Check (Code ⊆ Registry)
```
Checking coverage (code → shamefile)...
✓ All code suppressions are registered
```
**OR**
```
✗ Found 2 undocumented suppressions:
  - @ts-ignore at src/app.ts:42
  - # noqa at src/utils.py:101
```

### Step 3: Stale Check (Registry ⊆ Code)
```
Checking for stale entries (shamefile → code)...
✓ No stale entries
```
**OR**
```
✗ Found 1 stale entry:
  - # noqa at src/old.py:50 (not in code anymore)
```

### Step 4: Justification Check
```
Checking justifications...
✓ All entries have justifications
```
**OR**
```
✗ Found 3 entries without justification:
  - @ts-ignore at src/types.ts:15
  - # noqa at src/config.py:88
```

**Result**: FAIL if ANY step finds issues

---

## Suppression Budget System (HP Bar)

### Concept
- Registry has a **max_suppressions** cap (default: 1000)
- Each suppression = -1 HP
- Display as health bar: `████████████████████░ 988/1000 HP`
- At 0 HP = **LEGACY HELL** = block new suppressions

### Configuration
```yaml
config:
  version: "0.1.0"
  max_suppressions: 1000  # Configurable per project
```

### Health & Status
```bash
🎮 Code Health: ████████████████████░ 988/1000 HP

☠️  WARNING: If HP hits 0, you will go to LEGACY HELL.
```


### When Over Budget (Legacy Hell)
```bash
╔═══════════════════════════════════════╗
║     ☠️  You are in LEGACY HELL ☠️     ║
╚═══════════════════════════════════════╝

Health: ░░░░░░░░░░░░░░░░░░░░ 0/1000 HP (exceeded)
```

---

## Output Style: Fun by Default

### Philosophy
- Make it **memorable** (like `thefuck`)
- Make it **shareable** (viral potential)
- Make it **effective** (gamification works)
- Provide escape hatch (`--boring` flag)

### Fun Mode (default)
```bash
shame me

🎮 Code Health: ████████████████████░ 988/1000 HP
☠️  WARNING: If HP hits 0, you will go to LEGACY HELL.

✓ All suppressions are documented!
```

### Boring Mode (opt-in)
```bash
shame me --boring
```

---

## Registry Format (shamefile.yaml)

```yaml
config:
  version: "0.1.0"
  max_suppressions: 1000

entries:
  - file: src/app.py
    line: 42
    token: "# noqa"
    author: "John Doe <john@example.com>"
    created_at: 2024-01-15T10:30:00Z
    justification: "Legacy API doesn't have proper types, migration planned for Q2"

  - file: src/utils.ts
    line: 128
    token: "// @ts-ignore"
    author: "Jane Smith <jane@example.com>"
    created_at: 2024-01-20T14:22:00Z
    justification: "Third-party library has incorrect type definitions, reported in issue #123"
```

### Entry Fields
| Field | Required | Description |
|-------|----------|-------------|
| `file` | Yes | Relative path from repo root |
| `line` | Yes | Line number where suppression appears |
| `token` | Yes | Exact token matched (e.g., "# noqa") |
| `author` | Yes | Git user (auto-populated) |
| `created_at` | Yes | Timestamp (auto-populated) |
| `justification` | Yes | **Human-readable reason** (developer must provide) |

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

---

## Memory Considerations

### Typical Usage
| Suppressions | Memory | Status |
|-------------|--------|--------|
| 1,000 | 0.5 MB | ✅ Trivial |
| 10,000 | 5 MB | ✅ Easy |
| 100,000 | 50 MB | ✅ Fine |
| 1,000,000 | 480 MB | ⚠️ Tight but works |

**Calculation**: ~240 bytes per entry (registry) + ~160 bytes per violation (scan)

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

🎮 Code Health: ████████████████████░ 987/1000 HP

✗ Found 1 new suppression:
  + # noqa at src/app.py:42

Added to registry with empty justification.

✗ Validation failed! Add justifications to shamefile.yaml

exit code: 1

# Developer adds justification
vim shamefile.yaml
# justification: "False positive - linter bug #123"

# Commit again
git add shamefile.yaml
git commit -m "fix bug"

# Now passes
shame me

🎮 Code Health: ████████████████████░ 987/1000 HP

💚 EXCELLENT! No shame today!

✓ All suppressions are documented!
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

Step 1: Scanning code... ✓
Step 2: Coverage check... ✗ 1 undocumented
Step 3: Stale check... ✗ 2 stale entries
Step 4: Justifications... ✓

✗ Validation failed!

Run 'shame me' locally to sync.

exit code: 1
```

---

## Why This Design?

### 1. Single Command = Simple Mental Model
- `shame me` = "sync everything"
- `--dry-run` = "check only"
- No confusion between `check` vs `clean`

### 2. Gamification = Motivation
- HP bar makes tech debt **visible**
- Removing suppressions = +HP = feels good
- Teams compete: "Let's get back to 90% health!"

### 3. Fun = Viral Adoption
- Memorable tool name ("shame")
- Shareable screenshots (LEGACY HELL)
- Conference talk material
- Example: `thefuck` has 85K GitHub stars

### 4. Strict Validation = Quality
- 4-step validation catches everything
- No half-measures (stale entries = FAIL)
- Forces discipline

### 5. Escape Hatch = Flexibility
- `--boring` for corporate environments
- Configurable budget
- Doesn't force personality on everyone

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

### Team Leaderboard
```bash
shame leaderboard
# Show who added/removed most suppressions
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
- Twitter/Reddit mentions
- Conference talk acceptance

### Effectiveness
- % of projects that reduce suppressions after adopting
- Average health score improvement
- Developer feedback on gamification

### Viral Potential
- Screenshot shares (especially "LEGACY HELL")
- "Have you tried shame?" meme-ability
- Integration in popular projects

---

## Summary

**`shame`** is a suppression registry tool that:
- Enforces **documentation** of all code suppressions
- Uses **gamification** (HP bar) to motivate cleanup
- Has **personality** by default (fun, memorable, shareable)
- Provides **strict validation** (4-step check)
- Supports **CI/CD** (`--dry-run` mode)
- Stays **practical** (`--boring` escape hatch)

**Goal**: Make it the `thefuck` of linter enforcement - useful, memorable, and viral.