# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
