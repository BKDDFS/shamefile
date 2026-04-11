import subprocess

import yaml
from conftest import run_shamefile


def test_stale_entry_removed(tmp_path):
    """Removing suppression from code should remove its entry and exit 1."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # First run — creates entry, fill why
    run_shamefile(tmp_path)
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    # Developer removes suppression
    test_file.write_text("x = 1\n")

    # Second run — should remove stale entry and exit 1 (registry changed)
    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "Removing stale entry" in result.stdout
    assert "# noqa" not in registry.read_text()


def test_deleted_file_entries_become_stale(tmp_path):
    """Deleting a file with suppressions should remove its entries from registry."""
    file_a = tmp_path / "a.py"
    file_b = tmp_path / "b.py"
    file_a.write_text("x = 1  # noqa\n")
    file_b.write_text("y = 2  # type: ignore\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)
    assert "# noqa" in registry.read_text()
    assert "type: ignore" in registry.read_text()

    # Delete one file
    file_a.unlink()

    result = run_shamefile(tmp_path)

    registry_content = registry.read_text()
    assert "# noqa" not in registry_content
    assert "type: ignore" in registry_content
    assert "Removing stale entry" in result.stdout


def test_gitignored_file_entries_become_stale(tmp_path):
    """Adding a tracked file to .gitignore should remove its entries from registry."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # Need git repo for .gitignore to work
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)

    # First run — creates entry
    run_shamefile(tmp_path)
    assert "# noqa" in registry.read_text()
    (tmp_path / ".gitignore").write_text("test.py\n")

    # Second run — entry should be removed as stale
    result = run_shamefile(tmp_path)

    assert "Removing stale entry" in result.stdout
    assert "# noqa" not in registry.read_text()


def test_replacing_token_removes_old_and_adds_new(tmp_path):
    """Swapping one suppression for another should remove old entry and create new one."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # First run + fill why
    run_shamefile(tmp_path)
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    # Developer replaces token
    test_file.write_text("x = 1  # type: ignore\n")

    result = run_shamefile(tmp_path)

    registry_content = registry.read_text()
    assert "# noqa" not in registry_content
    assert "# type: ignore" in registry_content
    assert "Legacy code" not in registry_content
    assert "Removing stale entry" in result.stdout
    assert "New suppression detected" in result.stdout

    # New entry should have empty why (forces re-justification)
    entries = yaml.safe_load(registry_content)["entries"]
    new_entry = next(e for e in entries if e["token"] == "# type: ignore")  # noqa: S105
    assert new_entry["why"] == ""


def test_stale_removed_and_new_added_same_run(tmp_path):
    """Removing one file and adding another in same run should handle both correctly."""
    file_a = tmp_path / "a.py"
    file_b = tmp_path / "b.py"
    file_a.write_text("x = 1  # noqa\n")
    file_b.write_text("y = 2  # type: ignore\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)

    # Remove a.py, add c.py
    file_a.unlink()
    file_c = tmp_path / "c.py"
    file_c.write_text("z = 3  # nosec\n")

    result = run_shamefile(tmp_path)

    registry_content = registry.read_text()
    assert "# noqa" not in registry_content
    assert "# type: ignore" in registry_content
    assert "# nosec" in registry_content
    assert "Removing stale entry" in result.stdout
    assert "New suppression detected" in result.stdout


def test_multiple_stale_entries_removed_at_once(tmp_path):
    """Multiple stale entries should all be removed and exit 1."""
    (tmp_path / "a.py").write_text("x = 1  # noqa\n")
    (tmp_path / "b.py").write_text("y = 2  # type: ignore\n")
    (tmp_path / "c.py").write_text("z = 3  # nosec\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Legacy'"))

    # Remove all suppression files, add clean file
    (tmp_path / "a.py").unlink()
    (tmp_path / "b.py").unlink()
    (tmp_path / "c.py").unlink()
    (tmp_path / "clean.py").write_text("x = 1\n")

    result = run_shamefile(tmp_path)

    assert result.stdout.count("Removing stale entry") == 3
    assert result.returncode == 1
