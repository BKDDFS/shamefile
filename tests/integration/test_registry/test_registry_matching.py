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


@pytest.mark.xfail(reason="shame_vector not yet implemented")
def test_content_change_updates_shame_vector(tmp_path):
    """Changing line content should update shame_vector hash while preserving why."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry_path = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    original = yaml.safe_load(registry_path.read_text())["entries"][0]

    # Developer changes the code but keeps the suppression on the same line
    test_file.write_text("y = calculate()  # noqa\n")

    run_shamefile(str(tmp_path))

    registry = yaml.safe_load(registry_path.read_text())
    entry = registry["entries"][0]

    assert entry["why"] == "Legacy code"
    assert "shame_vector" in entry
    assert entry["shame_vector"] != original.get("shame_vector")


@pytest.mark.xfail(reason=XFAIL_MATCHING)
def test_line_shift_and_content_change_reports_unmatched(tmp_path):
    """Line shift + content change = unmatched, tool should not auto-remove."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry_path = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    # Developer changes both line and content
    test_file.write_text("\ny = calculate()  # noqa\n")

    result = run_shamefile(str(tmp_path))

    # Old entry should NOT be auto-removed
    registry = yaml.safe_load(registry_path.read_text())
    assert any(e["why"] == "Legacy code" for e in registry["entries"])
    assert "algorithmic matching failed" in result.stdout
