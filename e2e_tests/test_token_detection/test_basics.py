import subprocess

import pytest
import yaml
from conftest import EXTENSION_PARAMS, LANGUAGES, TOKEN_PARAMS, run_shamefile


@pytest.mark.parametrize(("token", "extension"), TOKEN_PARAMS)
def test_detects_token(token, extension, tmp_path):
    """Each tracked token should be detected in a file with the matching extension."""
    test_file = tmp_path / f"test{extension}"
    test_file.write_text(f"x = 1  {token}\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    tokens = {e["token"] for e in registry["entries"]}
    assert token.lower() in {t.lower() for t in tokens}
    assert "Added" in result.stdout


def test_detects_in_nested_dirs(tmp_path):
    """Tokens in deeply nested directories should all be found."""
    nested = tmp_path
    for i in range(10):
        nested = nested / f"level{i}"
    nested.mkdir(parents=True)

    (tmp_path / "root.py").write_text("x = 1  # noqa\n")
    (tmp_path / "level0" / "level1" / "mid.py").write_text("x = 1  # type: ignore\n")
    (nested / "deep.py").write_text("x = 1  # nosec\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "3 suppressions need documentation" in result.stdout
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    tokens = {e["token"] for e in registry["entries"]}
    assert "# noqa" in tokens
    assert "# type: ignore" in tokens
    assert "nosec" in tokens


def test_ignores_gitignored_files(tmp_path):
    """Files matching .gitignore patterns should not be scanned."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    (tmp_path / ".gitignore").write_text("ignored/\n")
    ignored_dir = tmp_path / "ignored"
    ignored_dir.mkdir()
    (ignored_dir / "hidden.py").write_text("x = 1  # noqa\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    assert registry["entries"] is None or len(registry["entries"]) == 0


def test_gitignore_not_respected_without_git_init(tmp_path):
    """Without git init, .gitignore should have no effect on scanning."""
    (tmp_path / ".gitignore").write_text("ignored/\n")
    ignored_dir = tmp_path / "ignored"
    ignored_dir.mkdir()
    (ignored_dir / "hidden.py").write_text("x = 1  # noqa\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    tokens = {e["token"] for e in registry["entries"]}
    assert "# noqa" in tokens


def test_multiple_files_multiple_languages(tmp_path):
    """One file per language extension should detect all their tokens."""
    expected_tokens = []
    for cfg in LANGUAGES.values():
        token = cfg["tokens"][0]
        ext = cfg["extensions"][0]
        (tmp_path / f"test.{ext}").write_text(f"x = 1  {token}\n")
        expected_tokens.append(token)

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert f"{len(expected_tokens)} suppressions need documentation" in result.stdout
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    found_tokens = {e["token"] for e in registry["entries"]}
    for token in expected_tokens:
        assert token in found_tokens


@pytest.mark.parametrize(("token", "extension"), EXTENSION_PARAMS)
def test_detects_token_in_each_extension(token, extension, tmp_path):
    """A token should be detected in every extension of its language."""
    test_file = tmp_path / f"test{extension}"
    test_file.write_text(f"x = 1  {token}\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    tokens = {e["token"] for e in registry["entries"]}
    assert token in tokens
    assert "Added" in result.stdout


def test_python_token_in_js_file_not_detected(tmp_path):
    """Python-specific token in a .js file should not be detected."""
    (tmp_path / "test.js").write_text("// # noqa\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry.get("entries") or []
    assert not any("noqa" in e["token"] for e in entries)


def test_js_token_in_py_file_not_detected(tmp_path):
    """JavaScript-specific token in a .py file should not be detected."""
    (tmp_path / "test.py").write_text("# // eslint-disable\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry.get("entries") or []
    assert not any("eslint-disable" in e["token"] for e in entries)
