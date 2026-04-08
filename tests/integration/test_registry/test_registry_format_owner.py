import os
import subprocess

import yaml

from conftest import BINARY_PATH, run_shamefile

# Environment that disables global/system git config
NO_GLOBAL_GIT = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
}


def run_shamefile_no_global_git(*args):
    """Run shamefile with global git config disabled."""
    return subprocess.run(
        [BINARY_PATH, "me", *args], capture_output=True, text=True, env=NO_GLOBAL_GIT
    )


def test_owner_from_git_blame_on_first_run(tmp_path):
    """On first shamefile creation, owner should come from git blame, not current user."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Alice"], cwd=tmp_path, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "alice@test.com"],
        cwd=tmp_path,
        capture_output=True,
    )

    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"], cwd=tmp_path, capture_output=True
    )

    # Switch to different user (simulates someone else running shamefile)
    subprocess.run(
        ["git", "config", "user.name", "Bob"], cwd=tmp_path, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "bob@test.com"],
        cwd=tmp_path,
        capture_output=True,
    )
    run_shamefile(str(tmp_path))

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    alice_entry = registry["entries"][0]
    assert alice_entry["owner"] == "Alice <alice@test.com>"


def test_owner_fallback_uncommitted_file(tmp_path):
    """Uncommitted file on first run — git blame fails, fallback to git config user."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Bob"], cwd=tmp_path, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "bob@test.com"],
        cwd=tmp_path,
        capture_output=True,
    )

    # File exists but is NOT committed — git blame will fail
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile(str(tmp_path))

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]

    # Fallback to git config user since blame fails on uncommitted file
    assert entry["owner"] == "Bob <bob@test.com>"


def test_owner_no_git_repo(tmp_path):
    """Without a git repo, owner should be 'Unknown'."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile_no_global_git(str(tmp_path))

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]
    assert entry["owner"] == "Unknown"


def test_owner_missing_name_only(tmp_path):
    """Git repo with only email should produce 'Unknown <email>'."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "alice@test.com"],
        cwd=tmp_path,
        capture_output=True,
    )

    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile_no_global_git(str(tmp_path))

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]
    assert entry["owner"] == "Unknown <alice@test.com>"


def test_owner_missing_name_and_email(tmp_path):
    """Git repo without user.name and user.email should produce 'Unknown'."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)

    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile_no_global_git(str(tmp_path))

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]
    assert entry["owner"] == "Unknown"
