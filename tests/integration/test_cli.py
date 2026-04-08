import subprocess

import yaml

from conftest import BINARY_PATH, run_shamefile


def test_dot_path_scans_current_directory(tmp_path):
    """'shame me .' should scan the current directory."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")

    result = subprocess.run(
        [BINARY_PATH, "me", "."], capture_output=True, text=True, cwd=tmp_path
    )

    assert result.returncode == 1
    assert (tmp_path / "shamefile.yaml").exists()


def test_no_path_defaults_to_current_directory(tmp_path):
    """'shame me' without path should default to scanning current directory."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")

    result = subprocess.run(
        [BINARY_PATH, "me"], capture_output=True, text=True, cwd=tmp_path
    )

    assert result.returncode == 1
    assert (tmp_path / "shamefile.yaml").exists()
