# shame-file

Centralized `# noqa` suppression registry for Python — every suppression needs a justification.

## Problem

`# noqa` comments silence linter warnings, but they rarely explain *why* a rule is suppressed. Over time, codebases accumulate unexplained suppressions that nobody dares to remove. There's no way to enforce that every `# noqa` has a documented reason, no way to set policies per rule, and no audit trail when suppressions appear or disappear.

**shame-file** fixes this by requiring every `# noqa` suppression to be registered in a central `.shame-file.toml` with a mandatory justification.

## How it works

1. A `.shame-file.toml` file at the repo root defines **rules** (per-code policies) and **overrides** (per-suppression registrations).
2. The `check` command compares every `# noqa` comment in your code against the registry — unregistered suppressions fail the check.
3. The `scan` command finds all `# noqa` comments in your code and generates override entries you can fill in.

### Matching strategy

Suppressions are matched by **file path + code + content hash**, not line numbers. The content hash is computed from the trimmed source line (excluding the `# noqa` comment itself). This means moving a line within the same file won't break the match — only changing the line's content will.

## Configuration

`.shame-file.toml` lives at the repository root:

```toml
[tool.shame-file]
exclude = ["tests/**", "migrations/**"]  # glob patterns to skip entirely

# Per-rule policies
[tool.shame-file.rules.E501]
allow = true          # allow this suppression without overrides (default: false)

[tool.shame-file.rules.F401]
allow = false         # every F401 suppression must have an override entry
max = 5              # fail if more than 5 F401 suppressions exist

# Individual suppression registrations
[[tool.shame-file.overrides]]
code = "F841"
path = "src/app/utils.py"
content_hash = "a1b2c3d4"
reason = "Variable used by exec() call two lines below"
pr = "https://github.com/org/repo/pull/42"

[[tool.shame-file.overrides]]
code = "E501"
path = "src/app/config.py"
content_hash = "e5f6a7b8"
reason = "Long URL in comment, splitting would reduce readability"
```

### Override fields

| Field          | Required | Description                                         |
|----------------|----------|-----------------------------------------------------|
| `code`         | yes      | The noqa rule code (e.g. `F841`, `E501`)            |
| `path`         | yes      | Relative file path from repo root                   |
| `content_hash` | yes      | Hash of the trimmed source line (auto-generated)    |
| `reason`       | yes      | Human-readable justification for the suppression    |
| `pr`           | no       | Link to the PR that introduced the suppression      |

## CLI Commands

### `shame-file check`

Validates that every `# noqa` comment in tracked files is registered in `.shame-file.toml`.

```bash
$ shame-file check
ERROR: Unregistered suppression:
  src/app/models.py:42  # noqa: F841
  Content hash: a1b2c3d4
  Register it in .shame-file.toml or run 'shame-file scan' to generate entries.

Found 1 unregistered suppression(s).
```

Exit code `1` if any unregistered suppressions are found, `0` otherwise.

Options:
- `--config PATH` — path to config file (default: `.shame-file.toml`)
- `--stats` — print summary statistics (total suppressions, per-rule counts)

### `shame-file scan`

Finds all `# noqa` comments and outputs override entries for unregistered ones.

```bash
$ shame-file scan
Found 3 unregistered suppression(s):

[[tool.shame-file.overrides]]
code = "F841"
path = "src/app/models.py"
content_hash = "a1b2c3d4"
reason = ""  # TODO: add justification

[[tool.shame-file.overrides]]
code = "E501"
path = "src/app/views.py"
content_hash = "b2c3d4e5"
reason = ""  # TODO: add justification
```

Options:
- `--config PATH` — path to config file (default: `.shame-file.toml`)
- `--append` — append new entries directly to the config file

## Pre-commit integration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/BKDDFS/shame-file
    rev: v0.1.0
    hooks:
      - id: shame-file-check
```

## Installation

```bash
pip install shame-file
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add --dev shame-file
```

## License

MIT