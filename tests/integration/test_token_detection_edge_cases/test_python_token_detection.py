import pytest

from conftest import (
    XFAIL_CASE_INSENSITIVE,
    XFAIL_STRING_DETECTION,
    XFAIL_WHITESPACE_VARIANT,
    run_shamefile,
)


@pytest.mark.xfail(reason=XFAIL_STRING_DETECTION)
def test_token_inside_docstring_is_not_detected(tmp_path):
    """Token inside a docstring is not a real suppression."""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        'def foo():\n    """Use # noqa for suppression."""\n    pass\n'
    )

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 0
    assert "# noqa" not in result.stdout


@pytest.mark.xfail(reason=XFAIL_CASE_INSENSITIVE)
def test_case_insensitive_noqa_not_detected(tmp_path):
    """# NOQA is valid Flake8 suppression but shamefile misses it."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # NOQA\n")

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1
    assert "New suppression detected" in result.stdout


@pytest.mark.xfail(reason=XFAIL_CASE_INSENSITIVE)
def test_case_insensitive_nosec_not_detected(tmp_path):
    """# NOSEC is valid Bandit suppression but shamefile misses it."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = dangerous_call()  # NOSEC\n")

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1
    assert "New suppression detected" in result.stdout


@pytest.mark.xfail(reason=XFAIL_CASE_INSENSITIVE)
def test_case_insensitive_pragma_not_detected(tmp_path):
    """# PRAGMA: NO COVER is valid Coverage.py suppression but shamefile misses it."""
    test_file = tmp_path / "test.py"
    test_file.write_text("if DEBUG:  # PRAGMA: NO COVER\n    pass\n")

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1
    assert "New suppression detected" in result.stdout


@pytest.mark.xfail(reason=XFAIL_WHITESPACE_VARIANT)
def test_no_space_after_hash_nosec_not_detected(tmp_path):
    """#nosec (no space after #) is valid Bandit suppression but shamefile misses it."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = dangerous_call()  #nosec\n")

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1
    assert "New suppression detected" in result.stdout


@pytest.mark.xfail(reason=XFAIL_WHITESPACE_VARIANT)
def test_extra_space_after_hash_noqa_not_detected(tmp_path):
    """#  noqa (extra space) is valid Flake8 suppression but shamefile misses it."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  #  noqa\n")

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1
    assert "New suppression detected" in result.stdout
