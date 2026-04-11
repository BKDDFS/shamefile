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


def run_shamefile_no_global_git(cwd, *args):
    """Run shamefile with global git config disabled."""
    return subprocess.run(
        [BINARY_PATH, "me", *args],
        capture_output=True,
        text=True,
        env=NO_GLOBAL_GIT,
        cwd=str(cwd),
        check=False,
    )


def test_owner_from_git_blame_on_first_run(tmp_path):
    """On first shamefile creation, owner should come from git blame, not current user."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Alice"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "alice@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    # Switch to different user (simulates someone else running shamefile)
    subprocess.run(
        ["git", "config", "user.name", "Bob"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "bob@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    run_shamefile(tmp_path)

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    alice_entry = registry["entries"][0]
    assert alice_entry["owner"] == "Alice <alice@test.com>"


def test_owner_from_git_blame_scanning_subdirectory(tmp_path):
    """'shame me src' from git root should still attribute owner via git blame."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Alice"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "alice@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("x = 1  # noqa\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    # Switch to different user
    subprocess.run(
        ["git", "config", "user.name", "Bob"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "bob@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    result = subprocess.run(
        [BINARY_PATH, "me", "src"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]
    assert entry["owner"] == "Alice <alice@test.com>"


def test_owner_fallback_uncommitted_file(tmp_path):
    """Uncommitted file on first run — git blame fails, fallback to git config user."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Bob"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "bob@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    # File exists but is NOT committed — git blame will fail
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile(tmp_path)

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]

    # Fallback to git config user since blame fails on uncommitted file
    assert entry["owner"] == "Bob <bob@test.com>"


def test_owner_no_git_repo(tmp_path):
    """Without a git repo, owner should be 'Unknown'."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile_no_global_git(tmp_path)

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]
    assert entry["owner"] == "Unknown"


def test_owner_missing_email_only(tmp_path):
    """Git repo with only name should produce 'Name <unknown@example.com>'."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Alice"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile_no_global_git(tmp_path)

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]
    assert entry["owner"] == "Alice <unknown@example.com>"


def test_owner_missing_name_only(tmp_path):
    """Git repo with only email should produce 'Unknown <email>'."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "alice@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile_no_global_git(tmp_path)

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]
    assert entry["owner"] == "Unknown <alice@test.com>"


def test_owner_missing_name_and_email(tmp_path):
    """Git repo without user.name and user.email should produce 'Unknown'."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)

    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile_no_global_git(tmp_path)

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]
    assert entry["owner"] == "Unknown"


def test_mixed_committed_and_uncommitted_owners(tmp_path):
    """First run: committed file gets blame owner, uncommitted gets current user."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Alice"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "alice@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    (tmp_path / "old.py").write_text("x = 1  # noqa\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True, check=True
    )

    # Switch to Bob
    subprocess.run(
        ["git", "config", "user.name", "Bob"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "bob@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    # new.py is NOT committed — blame will fail, fallback to current user
    (tmp_path / "new.py").write_text("y = 2  # type: ignore\n")

    run_shamefile(tmp_path)

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry["entries"]
    assert len(entries) == 2

    by_file = {e["location"].split(":")[0]: e for e in entries}
    assert by_file["old.py"]["owner"] == "Alice <alice@test.com>"
    assert by_file["new.py"]["owner"] == "Bob <bob@test.com>"


def test_staged_uncommitted_file_not_attributed_to_not_committed_yet(tmp_path):
    """Staged but uncommitted file should use fallback owner, not 'Not Committed Yet'."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Alice"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "alice@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    # Need at least one commit for blame to run (otherwise blame exits immediately)
    (tmp_path / "init.txt").write_text("init\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True, check=True
    )

    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    subprocess.run(
        ["git", "add", "test.py"], cwd=tmp_path, capture_output=True, check=True
    )
    # Staged but NOT committed

    run_shamefile(tmp_path)

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry["entries"]
    assert len(entries) == 1
    assert "Not Committed Yet" not in entries[0]["owner"]
    assert entries[0]["owner"] == "Alice <alice@test.com>"
