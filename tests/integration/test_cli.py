import subprocess

import pytest
import yaml

from conftest import BINARY_PATH, run_shamefile

XFAIL_REGISTRY_LOCATION = "shamefile.yaml is created in scan dir, should be at git root or CWD"


def test_dot_path_scans_current_directory(tmp_path):
    """'shame me .' should scan the current directory."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")

    result = subprocess.run(
        [BINARY_PATH, "me", "."], capture_output=True, text=True, cwd=tmp_path
    )

    assert result.returncode == 1
    assert (tmp_path / "shamefile.yaml").exists()


@pytest.mark.xfail(reason=XFAIL_REGISTRY_LOCATION)
def test_shamefile_created_in_cwd_not_scan_dir(tmp_path):
    """'shame me src' should create shamefile.yaml in CWD, not in src/."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "test.py").write_text("x = 1  # noqa\n")

    subprocess.run(
        [BINARY_PATH, "me", "src"], capture_output=True, text=True, cwd=tmp_path
    )

    assert (tmp_path / "shamefile.yaml").exists()
    assert not (src / "shamefile.yaml").exists()


@pytest.mark.xfail(reason=XFAIL_REGISTRY_LOCATION)
def test_shamefile_created_at_git_root(tmp_path):
    """Running from subdirectory of a git repo should create shamefile.yaml at git root."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    src = tmp_path / "src"
    src.mkdir()
    (src / "test.py").write_text("x = 1  # noqa\n")

    subprocess.run(
        [BINARY_PATH, "me", "."], capture_output=True, text=True, cwd=src
    )

    assert (tmp_path / "shamefile.yaml").exists()
    assert not (src / "shamefile.yaml").exists()


def test_no_path_defaults_to_current_directory(tmp_path):
    """'shame me' without path should default to scanning current directory."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")

    result = subprocess.run(
        [BINARY_PATH, "me"], capture_output=True, text=True, cwd=tmp_path
    )

    assert result.returncode == 1
    assert (tmp_path / "shamefile.yaml").exists()
