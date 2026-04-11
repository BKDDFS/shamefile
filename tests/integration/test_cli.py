import subprocess

import yaml
from conftest import BINARY_PATH


def test_dot_path_scans_current_directory(tmp_path):
    """'shame me .' should scan the current directory."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")

    result = subprocess.run(
        [BINARY_PATH, "me", "."],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 1
    assert (tmp_path / "shamefile.yaml").exists()


def test_shamefile_created_at_git_root(tmp_path):
    """Running from git repo subdir should create shamefile.yaml at git root."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    src = tmp_path / "src"
    src.mkdir()
    (src / "test.py").write_text("x = 1  # noqa\n")

    subprocess.run(
        [BINARY_PATH, "me", "."], capture_output=True, text=True, cwd=src, check=False
    )

    assert (tmp_path / "shamefile.yaml").exists()
    assert not (src / "shamefile.yaml").exists()


def test_shamefile_created_in_cwd_without_git(tmp_path):
    """Without a git repo, shamefile.yaml should be created in CWD."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "test.py").write_text("x = 1  # noqa\n")

    subprocess.run(
        [BINARY_PATH, "me", "src"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert (tmp_path / "shamefile.yaml").exists()
    assert not (src / "shamefile.yaml").exists()


def test_scan_path_scopes_what_is_scanned(tmp_path):
    """'shame me src' should only scan src/, not sibling directories."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "test.py").write_text("x = 1  # noqa\n")

    other = tmp_path / "other"
    other.mkdir()
    (other / "test.py").write_text("y = 2  # type: ignore\n")

    subprocess.run(
        [BINARY_PATH, "me", "src"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    # shamefile.yaml should be in CWD with entries only from src/
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry["entries"]
    assert len(entries) == 1
    assert "# noqa" in entries[0]["token"]


def test_single_file_path_scans_that_file(tmp_path):
    """'shame me src/app.py' should scan that single file."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("x = 1  # noqa\n")
    (src / "utils.py").write_text("y = 2  # type: ignore\n")

    result = subprocess.run(
        [BINARY_PATH, "me", "src/app.py"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 1
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry["entries"]
    assert len(entries) == 1
    assert "# noqa" in entries[0]["token"]


def test_single_file_with_git_uses_git_root(tmp_path):
    """'shame me app.py' from subdir of git repo should place registry at git root."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("x = 1  # noqa\n")

    subprocess.run(
        [BINARY_PATH, "me", "app.py"],
        capture_output=True,
        text=True,
        cwd=src,
        check=False,
    )

    assert (tmp_path / "shamefile.yaml").exists()
    assert not (src / "shamefile.yaml").exists()


def test_single_file_without_git_uses_cwd(tmp_path):
    """Without git, registry should be placed at CWD, not file's directory."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("x = 1  # noqa\n")

    subprocess.run(
        [BINARY_PATH, "me", "src/app.py"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert (tmp_path / "shamefile.yaml").exists()
    assert not (src / "shamefile.yaml").exists()


def test_no_path_defaults_to_current_directory(tmp_path):
    """'shame me' without path should default to scanning current directory."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")

    result = subprocess.run(
        [BINARY_PATH, "me"], capture_output=True, text=True, cwd=tmp_path, check=False
    )

    assert result.returncode == 1
    assert (tmp_path / "shamefile.yaml").exists()
