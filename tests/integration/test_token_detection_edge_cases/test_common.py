import pytest

from conftest import PYTHON_TOKENS, XFAIL_STRING_DETECTION, run_shamefile


def test_token_with_error_code(tmp_path):
    """Token followed by an error code should still be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa: E501\n")

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1
    assert "# noqa" in result.stdout


def test_multiple_tokens_on_one_line(tmp_path):
    """All Python suppressions on one line should all be detected."""
    line = "x = 1  " + "  ".join(PYTHON_TOKENS) + "\n"
    test_file = tmp_path / "test.py"
    test_file.write_text(line)

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1
    assert f"Found {len(PYTHON_TOKENS)} suppressions" in result.stdout
    for token in PYTHON_TOKENS:
        assert token in result.stdout


def test_token_with_trailing_text(tmp_path):
    """Token followed by extra text (e.g. '# nosec B324 -- not crypto') should be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        "checksum = hashlib.md5(data).hexdigest()  # nosec B324\n"
    )

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1
    assert "# nosec" in result.stdout


@pytest.mark.xfail(reason=XFAIL_STRING_DETECTION)
def test_token_inside_string_is_not_detected(tmp_path):
    """Token inside a string literal is not a real suppression and should not be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_text('msg = "use # noqa to suppress warnings"\n')

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 0
    assert "# noqa" not in result.stdout


@pytest.mark.xfail(reason="scanner has no extension filter — scans all files including non-code")
def test_non_code_files_not_scanned(tmp_path):
    """Tokens in non-code files (.md, .json) should not be detected."""
    (tmp_path / "README.md").write_text("Use `# noqa` to suppress linting warnings.\n")
    (tmp_path / "config.json").write_text('{"rule": "// eslint-disable"}\n')

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 0
