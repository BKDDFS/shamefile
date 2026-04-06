import pytest
import yaml

from conftest import run_shamefile


@pytest.fixture
def single_entry(tmp_path):
    """Create a file with one suppression, run shamefile, return the entry."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    run_shamefile(str(tmp_path))
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    return registry["entries"][0]


def test_entry_has_correct_token(single_entry):
    """Entry token should match the detected suppression."""
    assert single_entry["token"] == "# noqa"


def test_entry_has_correct_location(single_entry):
    """Entry location should contain file path and line number."""
    assert single_entry["location"].endswith("test.py:1")


def test_entry_has_empty_why_on_creation(single_entry):
    """New entry should have empty why, waiting for developer to fill in."""
    assert single_entry["why"] == ""


def test_entry_has_recent_created_at(single_entry):
    """Entry created_at should be a recent UTC timestamp."""
    from datetime import datetime, timedelta, timezone

    created_at = single_entry["created_at"]
    now = datetime.now(timezone.utc)

    assert isinstance(created_at, datetime)
    assert now - created_at < timedelta(minutes=5)


def test_entry_location_matches_line_position(tmp_path):
    """Location line number should match actual position in file."""
    test_file = tmp_path / "test.py"
    test_file.write_text("clean\nclean\nx = 1  # noqa\n")

    run_shamefile(str(tmp_path))

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]

    assert entry["location"].endswith("test.py:3")


def test_entry_location_includes_nested_path(tmp_path):
    """Location should include full path for files in subdirectories."""
    nested = tmp_path / "src" / "deep"
    nested.mkdir(parents=True)
    test_file = nested / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile(str(tmp_path))

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]

    assert "src/deep/test.py:1" in entry["location"]


def test_entry_location_with_spaces_in_path(tmp_path):
    """Location should handle spaces in directory and file names."""
    spaced = tmp_path / "my project" / "sub dir"
    spaced.mkdir(parents=True)
    test_file = spaced / "my file.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile(str(tmp_path))

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]

    assert "my project/sub dir/my file.py:1" in entry["location"]


def test_rerun_produces_same_yaml(tmp_path):
    """Running shame me twice without changes should produce identical YAML."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry_path = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))
    first_content = registry_path.read_text()

    run_shamefile(str(tmp_path))
    second_content = registry_path.read_text()

    assert first_content == second_content


def test_owner_from_git_blame_on_first_run(tmp_path):
    """On first shamefile creation, owner should come from git blame, not current user."""
    import subprocess

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
    import subprocess

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
