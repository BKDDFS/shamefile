import pytest
import yaml

from conftest import run_shamefile

XFAIL_MATCHING = "shame_vector and cascade matching not yet implemented"


@pytest.fixture
def line_shifted_entry(tmp_path):
    """Create entry by Alice, shift line, Bob reruns, return (original_entry, new_entry)."""
    import subprocess

    # Init repo as Alice
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

    # First run — Alice's suppression, Alice as owner (via git blame)
    run_shamefile(str(tmp_path))
    registry_path = tmp_path / "shamefile.yaml"
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    original = yaml.safe_load(registry_path.read_text())["entries"][0]

    # Switch to Bob
    subprocess.run(
        ["git", "config", "user.name", "Bob"], cwd=tmp_path, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "bob@test.com"],
        cwd=tmp_path,
        capture_output=True,
    )

    # Developer adds a blank line above — suppression shifts from line 1 to line 2
    test_file.write_text("\nx = 1  # noqa\n")
    run_shamefile(str(tmp_path))

    updated = yaml.safe_load(registry_path.read_text())["entries"][0]
    return original, updated


@pytest.mark.xfail(reason=XFAIL_MATCHING)
def test_line_shift_preserves_why(line_shifted_entry):
    """Suppression moving to a different line should preserve why."""
    _, entry = line_shifted_entry
    assert entry["why"] == "Legacy code"


@pytest.mark.xfail(reason=XFAIL_MATCHING)
def test_line_shift_preserves_owner(line_shifted_entry):
    """Suppression moving to a different line should preserve owner."""
    original, entry = line_shifted_entry
    assert entry["owner"] == original["owner"]


@pytest.mark.xfail(reason=XFAIL_MATCHING)
def test_line_shift_preserves_created_at(line_shifted_entry):
    """Suppression moving to a different line should preserve created_at."""
    original, entry = line_shifted_entry
    assert entry["created_at"] == original["created_at"]


def test_line_shift_updates_location(line_shifted_entry):
    """Suppression moving to a different line should update location."""
    _, entry = line_shifted_entry
    assert entry["location"].endswith(":2")


@pytest.fixture
def two_entries_shifted(tmp_path):
    """Create two entries, shift both lines, rerun, return (originals, updated)."""
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
    test_file.write_text("x = 1  # noqa\ny = 2  # type: ignore\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"], cwd=tmp_path, capture_output=True
    )

    run_shamefile(str(tmp_path))
    registry_path = tmp_path / "shamefile.yaml"
    content = registry_path.read_text()
    content = content.replace("why: ''", "why: 'Justified'")
    registry_path.write_text(content)

    originals = yaml.safe_load(registry_path.read_text())["entries"]

    # Add blank line at top — both shift by 1
    test_file.write_text("\nx = 1  # noqa\ny = 2  # type: ignore\n")
    run_shamefile(str(tmp_path))

    updated = yaml.safe_load(registry_path.read_text())["entries"]
    return originals, updated


@pytest.mark.xfail(reason=XFAIL_MATCHING)
def test_multiple_entries_shift_simultaneously(two_entries_shifted):
    """Multiple entries shifting at once should all preserve why."""
    _, updated = two_entries_shifted
    assert all(e["why"] == "Justified" for e in updated)


@pytest.mark.xfail(reason=XFAIL_MATCHING)
def test_one_shifts_one_stays(tmp_path):
    """One entry shifts, another stays — both should preserve why."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n\ny = 2  # type: ignore\n")
    registry_path = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Justified'"))

    # Insert line between them — only second shifts
    test_file.write_text("x = 1  # noqa\nnew line\n\ny = 2  # type: ignore\n")

    run_shamefile(str(tmp_path))

    registry = yaml.safe_load(registry_path.read_text())
    assert all(e["why"] == "Justified" for e in registry["entries"])


@pytest.mark.xfail(reason=XFAIL_MATCHING)
def test_large_line_shift(tmp_path):
    """Suppression shifting by many lines should still preserve why."""
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

    run_shamefile(str(tmp_path))
    registry_path = tmp_path / "shamefile.yaml"
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    # Shift by 20 lines
    test_file.write_text("\n" * 20 + "x = 1  # noqa\n")

    run_shamefile(str(tmp_path))

    registry = yaml.safe_load(registry_path.read_text())
    entry = registry["entries"][0]

    assert entry["why"] == "Legacy code"
