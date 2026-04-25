#!/usr/bin/env bash
# Reproduce SonarCloud's coverage run locally.
#
# Builds an instrumented binary, runs both Rust unit tests and the Python
# integration suite against it, then merges the profile data into lcov.info.
# Pass --html to also open an interactive report at target/llvm-cov/html/index.html.

set -euo pipefail

cd "$(dirname "$0")/.."

eval "$(cargo llvm-cov show-env --export-prefix)"

cargo llvm-cov clean --workspace
cargo build --all-features --workspace
cargo test --all-features --workspace
uv run pytest tests/ -n auto

cargo llvm-cov report --lcov --output-path lcov.info
cargo llvm-cov report --summary-only

if [[ "${1:-}" == "--html" ]]; then
  cargo llvm-cov report --html
  echo "HTML report: target/llvm-cov/html/index.html"
fi
