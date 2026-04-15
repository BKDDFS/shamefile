import yaml
from conftest import LANGUAGES, run_shamefile

PYTHON_TOKENS = LANGUAGES["Python"]["tokens"]


def test_token_with_error_code(tmp_path):
    """Token followed by an error code should still be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa: E501\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    assert any(e["token"] == "# noqa" for e in registry["entries"])  # noqa: S105


def test_multiple_tokens_on_one_line(tmp_path):
    """All Python suppressions on one line should all be detected."""
    line = "x = 1  " + "  ".join(PYTHON_TOKENS) + "\n"
    test_file = tmp_path / "test.py"
    test_file.write_text(line)

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert f"{len(PYTHON_TOKENS)} suppressions need documentation" in result.stdout
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    found_tokens = {e["token"] for e in registry["entries"]}
    for token in PYTHON_TOKENS:
        assert token in found_tokens


def test_token_with_trailing_text(tmp_path):
    """Token followed by extra text (e.g. '# nosec B324 -- not crypto') should be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_text("checksum = hashlib.md5(data).hexdigest()  # nosec B324\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    assert any(e["token"] == "nosec" for e in registry["entries"])  # noqa: S105


def test_token_inside_string_is_not_detected(tmp_path):
    """Token inside a string literal is not a real suppression and should not be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_text('msg = "use # noqa to suppress warnings"\n')

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry.get("entries") or []
    assert not any("noqa" in e["token"] for e in entries)


def test_token_in_file_with_syntax_errors_is_still_detected(tmp_path):
    """Syntax errors should not prevent token detection (graceful degradation)."""
    test_file = tmp_path / "broken.py"
    test_file.write_text("def foo(\n    x = 1  # noqa\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    assert any(e["token"] == "# noqa" for e in registry["entries"])  # noqa: S105


def test_non_code_files_not_scanned(tmp_path):
    """Tokens in non-code files (.md, .json) should not be detected."""
    (tmp_path / "README.md").write_text("Use `# noqa` to suppress linting warnings.\n")
    (tmp_path / "config.json").write_text('{"rule": "// eslint-disable"}\n')

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
