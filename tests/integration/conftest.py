import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
TOKENS_RS_PATH = PROJECT_ROOT / "src" / "tokens.rs"
BINARY_PATH = str(PROJECT_ROOT / "target" / "debug" / "shame")

PYTHON_TOKENS = [
    "# noqa",
    "# pylint: disable",
    "# type: ignore",
    "# pyright: ignore",
    "# pytype: disable",
    "# pyre-ignore",
    "# pyre-fixme",
    "# nosec",
    "# pragma: no cover",
    "# fmt: off",
    "# fmt: skip",
    "# isort: skip",
    "# lint-fixme",
    "# lint-ignore",
    "# autopep8: off",
]

JAVASCRIPT_TOKENS = [
    "// eslint-disable",
    "/* eslint-disable",
]

TYPESCRIPT_TOKENS = [
    "// tslint:disable",
    "/* tslint:disable",
    "// @ts-ignore",
    "/* @ts-ignore",
    "// @ts-expect-error",
    "/* @ts-expect-error",
]

ALL_TOKENS = PYTHON_TOKENS + JAVASCRIPT_TOKENS + TYPESCRIPT_TOKENS

LANGUAGE_TOKENS = {
    ".py": PYTHON_TOKENS,
    ".js": JAVASCRIPT_TOKENS,
    ".ts": TYPESCRIPT_TOKENS,
}

TOKEN_PARAMS = [
    (token, extension) for extension, tokens in LANGUAGE_TOKENS.items() for token in tokens
]


XFAIL_STRING_DETECTION = "grep-based scanner doesn't understand language syntax"
XFAIL_WHITESPACE_VARIANT = (
    "Python-only: Flake8, Bandit accept whitespace variants but shamefile uses exact match"
)
XFAIL_BLOCK_COMMENT = "shamefile only tracks // comment style, not /* */ block comments"


def run_shamefile(cwd, *args):
    """Run the shamefile binary with 'me' subcommand in a specific working directory."""
    return subprocess.run(
        [BINARY_PATH, "me", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        check=False,
    )


def parse_tokens_from_rust_source() -> list[str]:
    """Parse TRACKED_TOKENS from src/tokens.rs as plain text."""
    content = TOKENS_RS_PATH.read_text()
    return re.findall(r'"([^"]+)"', content.split("TRACKED_TOKENS")[1].split(";")[0])
