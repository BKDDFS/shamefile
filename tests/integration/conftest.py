import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
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
            "# nosec",
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


XFAIL_WHITESPACE_VARIANT = (
    "Python-only: Flake8, Bandit accept whitespace variants but shamefile uses exact match"
)


def run_shamefile(cwd, *args):
    """Run the shamefile binary with 'me' subcommand in a specific working directory."""
    return subprocess.run(
        [BINARY_PATH, "me", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        check=False,
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
