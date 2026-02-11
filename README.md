# shamefile

A centralized registry for code suppressions.

This tool enforces validation of lint suppressions by requiring them to be documented in a central `shamefile.yaml` registry.

It is **language-agnostic** and supports finding suppressions in various languages:

- **Python/YAML/Shell**: `# noqa`
- **JavaScript/TypeScript**: `// eslint-disable`, `// tslint:disable`, `// @ts-ignore`, `// @ts-expect-error`
- **General**: `# NOSONAR`, `# pragma: no cover`

## Installation

```bash
pip install shamefile
```

## Usage

```bash
# Check for undocumented suppressions
shame check .

# Clean stale entries
shame me .
```
