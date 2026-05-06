import os
import re
import subprocess
from pathlib import Path

# Strip GIT_* vars at conftest-import time so subprocess git calls in tests
# don't leak the parent repo's .git, hooks path, or index. This happens when
# pytest runs under a git hook (e.g. `git push`'s pre-push) that exports
# GIT_DIR / GIT_INDEX_FILE for hook execution. Doing this at import (not in
# an autouse fixture) ensures module-level snapshots like NO_GLOBAL_GIT in
# test_registry_format_owner.py are clean before they are captured.
for _k in [k for k in os.environ if k.startswith("GIT_")]:
    del os.environ[_k]

PROJECT_ROOT = Path(__file__).parent.parent
LANGUAGES_RS_PATH = PROJECT_ROOT / "src" / "languages.rs"
BINARY_PATH = str(PROJECT_ROOT / "target" / "debug" / "shame")

LANGUAGES = {
    "Python": {
        "extensions": ["py"],
        "tokens": [
            "# noqa",
            "# pylint: disable",
            "# type: ignore",
            "# pyright: ignore",
            "# pytype: disable",
            "# pyre-ignore",
            "# pyre-fixme",
            "nosec",
            "# pragma: no cover",
            "# fmt: off",
            "# fmt: skip",
            "# isort: skip",
            "# lint-fixme",
            "# lint-ignore",
            "# autopep8: off",
        ],
    },
    "JavaScript": {
        "extensions": ["js", "jsx", "mjs", "cjs"],
        "tokens": [
            "// eslint-disable",
            "/* eslint-disable",
            "// @ts-ignore",
            "/* @ts-ignore",
            "// @ts-expect-error",
            "/* @ts-expect-error",
        ],
    },
    "TypeScript": {
        "extensions": ["ts"],
        "tokens": [
            "// eslint-disable",
            "/* eslint-disable",
            "// tslint:disable",
            "/* tslint:disable",
            "// @ts-ignore",
            "/* @ts-ignore",
            "// @ts-expect-error",
            "/* @ts-expect-error",
        ],
    },
    "TypeScript (TSX)": {
        "extensions": ["tsx"],
        "tokens": [
            "// eslint-disable",
            "/* eslint-disable",
            "// tslint:disable",
            "/* tslint:disable",
            "// @ts-ignore",
            "/* @ts-ignore",
            "// @ts-expect-error",
            "/* @ts-expect-error",
        ],
    },
}

TOKEN_PARAMS = [
    (token, f".{cfg['extensions'][0]}") for cfg in LANGUAGES.values() for token in cfg["tokens"]
]

EXTENSION_PARAMS = [
    (cfg["tokens"][0], f".{ext}") for cfg in LANGUAGES.values() for ext in cfg["extensions"]
]


def run_shamefile(cwd, *args):
    """Run the shamefile binary with 'me' subcommand in a specific working directory."""
    return subprocess.run(
        [BINARY_PATH, "me", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        check=False,
    )


def run_shame_next(cwd):
    """Run 'shame next' in a specific working directory."""
    return subprocess.run(
        [BINARY_PATH, "next"],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        check=False,
    )


def run_shame_fix(cwd, *args):
    """Run 'shame fix' in a specific working directory."""
    return subprocess.run(
        [BINARY_PATH, "fix", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        check=False,
    )


def run_shame_remove(cwd, *args):
    """Run 'shame remove' in a specific working directory."""
    return subprocess.run(
        [BINARY_PATH, "remove", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        check=False,
    )


def git_init(path, user="Alice", email="alice@test.com"):
    """Initialize a git repo with user config. Returns path."""
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.name", user],
        cwd=path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", email],
        cwd=path,
        capture_output=True,
        check=True,
    )
    return path


def git_commit(path, message="commit"):
    """Stage all and commit."""
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=path,
        capture_output=True,
        check=True,
    )


def parse_languages_from_rust_source() -> dict:
    """Parse LANGUAGES from src/languages.rs, returning {name: {extensions, tokens}}."""
    content = LANGUAGES_RS_PATH.read_text()
    languages = {}
    for raw_block in content.split("Language {")[1:]:
        block = raw_block.split("},")[0]
        name_match = re.search(r'name:\s*"([^"]+)"', block)
        if not name_match:
            continue
        name = name_match.group(1)
        ext_section = block.split("extensions:")[1].split("],")[0]
        extensions = re.findall(r'"([^"]+)"', ext_section)
        tok_section = block.split("tokens:")[1].split("],")[0]
        tokens = re.findall(r'"([^"]+)"', tok_section)
        languages[name] = {"extensions": extensions, "tokens": tokens}
    return languages
