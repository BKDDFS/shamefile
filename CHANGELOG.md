# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.7](https://github.com/BKDDFS/shamefile/compare/v0.1.6...v0.1.7) - 2026-05-17

### Other

- bump github/codeql-action from 4.35.4 to 4.35.5 ([#78](https://github.com/BKDDFS/shamefile/pull/78))

## [0.1.6](https://github.com/BKDDFS/shamefile/compare/v0.1.5...v0.1.6) - 2026-05-16

### Other

- *(readme)* hero banner, benefits section, compressed assets ([#73](https://github.com/BKDDFS/shamefile/pull/73))
- cover non-Windows strip_registry_prefix_fallback ([#72](https://github.com/BKDDFS/shamefile/pull/72))

## [0.1.5](https://github.com/BKDDFS/shamefile/compare/v0.1.4...v0.1.5) - 2026-05-11

### Fixed

- normalize Windows absolute registry paths ([#70](https://github.com/BKDDFS/shamefile/pull/70))

### Other

- *(sonar)* skip scan for fork PRs ([#71](https://github.com/BKDDFS/shamefile/pull/71))
- bump taiki-e/install-action from 2.75.29 to 2.77.3 ([#66](https://github.com/BKDDFS/shamefile/pull/66))
- bump actions/dependency-review-action from 4.9.0 to 5.0.0 ([#67](https://github.com/BKDDFS/shamefile/pull/67))
- bump github/codeql-action from 4.35.3 to 4.35.4 ([#68](https://github.com/BKDDFS/shamefile/pull/68))

## [0.1.4](https://github.com/BKDDFS/shamefile/compare/v0.1.3...v0.1.4) - 2026-05-06

### Added

- *(cli)* add `shame remove` command (closes #48) ([#64](https://github.com/BKDDFS/shamefile/pull/64))

## [0.1.3](https://github.com/BKDDFS/shamefile/compare/v0.1.2...v0.1.3) - 2026-05-05

### Fixed

- release-plz, pre-launch FAQ, contributing ([#62](https://github.com/BKDDFS/shamefile/pull/62))
- drop MSRV to 1.88 and tighten README sample accuracy

## [0.1.2](https://github.com/BKDDFS/shamefile/compare/v0.1.1...v0.1.2) - 2026-05-04

### Fixed

- *(registry)* Emit date-only timestamps in `shamefile.yaml`

### Documentation

- Add logo and rewrite README intro

### Other

- *(tests)* Rename `tests/integration` to `e2e_tests`
- *(linguist)* Exclude `e2e_tests` from language stats
- Dogfood shamefile on this repo

## [0.1.1](https://github.com/BKDDFS/shamefile/compare/v0.1.0...v0.1.1) - 2026-05-04

### Fixed

- Declare `pre-commit` as a required Python dependency

## [0.1.0](https://github.com/BKDDFS/shamefile/releases/tag/v0.1.0) - 2026-04-25

First stable release. shamefile turns linter suppressions (`# noqa`, `// eslint-disable-next-line`, `# type: ignore`, `# nosec`, etc.) from silent technical debt into reviewable, documented decisions — every suppression must come with an owner and a `why`, enforced in CI via `shame me --dry-run`.
