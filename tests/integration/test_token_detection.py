import subprocess

import pytest

from conftest import LANGUAGE_TOKENS, TOKEN_PARAMS, run_shamefile


@pytest.mark.parametrize("token, extension", TOKEN_PARAMS)
def test_detects_token(token, extension, tmp_path):
    test_file = tmp_path / f"test{extension}"
    test_file.write_text(f"x = 1  {token}\n")

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1
    assert token in result.stdout
    assert "New suppression detected" in result.stdout


def test_detects_in_nested_dirs(tmp_path):
    nested = tmp_path
    for i in range(10):
        nested = nested / f"level{i}"
    nested.mkdir(parents=True)

    (tmp_path / "root.py").write_text("x = 1  # noqa\n")
    (tmp_path / "level0" / "level1" / "mid.py").write_text("x = 1  # type: ignore\n")
    (nested / "deep.py").write_text("x = 1  # nosec\n")

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1
    assert "Found 3 suppressions in code" in result.stdout
    assert "# noqa" in result.stdout
    assert "# type: ignore" in result.stdout
    assert "# nosec" in result.stdout


def test_ignores_gitignored_files(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    (tmp_path / ".gitignore").write_text("ignored/\n")
    ignored_dir = tmp_path / "ignored"
    ignored_dir.mkdir()
    (ignored_dir / "hidden.py").write_text("x = 1  # noqa\n")

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 0
    assert "# noqa" not in result.stdout


def test_gitignore_not_respected_without_git_init(tmp_path):
    (tmp_path / ".gitignore").write_text("ignored/\n")
    ignored_dir = tmp_path / "ignored"
    ignored_dir.mkdir()
    (ignored_dir / "hidden.py").write_text("x = 1  # noqa\n")

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1
    assert "# noqa" in result.stdout


def test_multiple_files_multiple_languages(tmp_path):
    expected_tokens = []
    for ext, tokens in LANGUAGE_TOKENS.items():
        token = tokens[0]
        (tmp_path / f"test{ext}").write_text(f"x = 1  {token}\n")
        expected_tokens.append(token)

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1
    assert f"Found {len(expected_tokens)} suppressions" in result.stdout
    for token in expected_tokens:
        assert token in result.stdout
