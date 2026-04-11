from conftest import run_shamefile


def test_token_inside_docstring_is_not_detected(tmp_path):
    """Token inside a docstring is not a real suppression."""
    test_file = tmp_path / "test.py"
    test_file.write_text('def foo():\n    """Use # noqa for suppression."""\n    pass\n')

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    assert "# noqa" not in result.stdout


def test_token_inside_multiline_string_is_not_detected(tmp_path):
    """Token inside a triple-quoted string (not docstring) is not a real suppression."""
    test_file = tmp_path / "test.py"
    test_file.write_text('msg = """\nuse # noqa to suppress\nwarnings\n"""\n')

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    assert "# noqa" not in result.stdout


def test_token_in_comment_next_to_string_is_detected(tmp_path):
    """Token in a comment on the same line as a string should be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_text('msg = "hello"  # noqa\n')

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "# noqa" in result.stdout


def test_token_in_string_and_comment_same_line(tmp_path):
    """Token appearing in both string and comment — the comment is real, should be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_text('msg = "# noqa"  # noqa\n')

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "# noqa" in result.stdout


def test_case_insensitive_noqa_detected(tmp_path):
    """# NOQA is valid Flake8 suppression and should be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # NOQA\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "New suppression detected" in result.stdout


def test_case_insensitive_nosec_detected(tmp_path):
    """# NOSEC is valid Bandit suppression and should be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = dangerous_call()  # NOSEC\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "New suppression detected" in result.stdout


def test_case_insensitive_pragma_detected(tmp_path):
    """# PRAGMA: NO COVER is valid Coverage.py suppression and should be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_text("if DEBUG:  # PRAGMA: NO COVER\n    pass\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "New suppression detected" in result.stdout


def test_no_space_after_hash_nosec_detected(tmp_path):
    """#nosec (no space after #) is valid Bandit suppression and should be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = dangerous_call()  #nosec\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "New suppression detected" in result.stdout


def test_extra_space_after_hash_nosec_detected(tmp_path):
    """#  nosec (extra space) is valid Bandit suppression and should be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = dangerous_call()  #  nosec\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "New suppression detected" in result.stdout
