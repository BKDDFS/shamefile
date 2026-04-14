import subprocess

import yaml
from conftest import BINARY_PATH, run_shamefile


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
    assert "nosec" in registry_content
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

    stale_count = 3  # a.py, b.py, c.py all deleted
    assert result.stdout.count("Removing stale entry") == stale_count
    assert result.returncode == 1


def test_narrower_scan_preserves_out_of_scope_entries(tmp_path):
    """Rerunning with fewer paths should not remove entries from unscanned paths."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("x = 1  # noqa\n")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_foo.py").write_text("y = 2  # type: ignore\n")

    # First run: scan both directories
    subprocess.run(
        [BINARY_PATH, "me", "src", "tests"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    registry_path = tmp_path / "shamefile.yaml"
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Justified'"))

    # Second run: scan only src (forgot tests)
    result = subprocess.run(
        [BINARY_PATH, "me", "src"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    entries = yaml.safe_load(registry_path.read_text())["entries"]
    tokens = {e["token"] for e in entries}
    assert "# type: ignore" in tokens, "Entry from tests/ should survive narrower scan"
    assert "Removing stale entry" not in result.stdout
    assert result.returncode == 0


def test_single_file_scan_preserves_other_entries(tmp_path):
    """Scanning a single file should not remove entries from other files."""
    (tmp_path / "a.py").write_text("x = 1  # noqa\n")
    (tmp_path / "b.py").write_text("y = 2  # type: ignore\n")

    # First run: scan everything
    run_shamefile(tmp_path)
    registry_path = tmp_path / "shamefile.yaml"
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Justified'"))

    # Second run: scan only a.py
    result = subprocess.run(
        [BINARY_PATH, "me", "a.py"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    entries = yaml.safe_load(registry_path.read_text())["entries"]
    tokens = {e["token"] for e in entries}
    assert "# type: ignore" in tokens, "Entry from b.py should survive single-file scan"
    assert result.returncode == 0


def test_subdir_scan_after_full_scan_preserves_other_entries(tmp_path):
    """'shame me src' after 'shame me .' should not remove entries outside src/."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("x = 1  # noqa\n")
    (tmp_path / "root.py").write_text("y = 2  # type: ignore\n")

    # First run: scan everything
    run_shamefile(tmp_path)
    registry_path = tmp_path / "shamefile.yaml"
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Justified'"))

    # Second run: scan only src/
    result = subprocess.run(
        [BINARY_PATH, "me", "src"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    entries = yaml.safe_load(registry_path.read_text())["entries"]
    tokens = {e["token"] for e in entries}
    assert "# type: ignore" in tokens, "Entry from root.py should survive src-only scan"
    assert result.returncode == 0


def test_absolute_path_entry_detected_as_stale(tmp_path):
    """Entry with absolute path in location should still be detected as stale."""
    (tmp_path / "a.py").write_text("x = 1  # noqa\n")
    registry_path = tmp_path / "shamefile.yaml"

    # Create registry with one valid entry and one stale entry using absolute path
    data = {
        "config": {},
        "entries": [
            {
                "location": "a.py:1",
                "token": "# noqa",
                "shame_vector": "sv1:0000000000000000",
                "owner": "Test <test@test.com>",
                "created_at": "2026-01-01T00:00:00Z",
                "why": "Valid",
            },
            {
                "location": f"{tmp_path}/deleted.py:1",
                "token": "# noqa",
                "shame_vector": "sv1:0000000000000000",
                "owner": "Test <test@test.com>",
                "created_at": "2026-01-01T00:00:00Z",
                "why": "Should be removed",
            },
        ],
    }
    registry_path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))

    result = run_shamefile(tmp_path)

    entries = yaml.safe_load(registry_path.read_text())["entries"]
    locations = [e["location"] for e in entries]
    assert "a.py:1" in locations
    assert not any("deleted.py" in loc for loc in locations), (
        "Entry with absolute path for non-existent file should be removed as stale"
    )
    assert "Removing stale entry" in result.stdout


def test_absolute_path_entry_stale_with_scoped_scan(tmp_path):
    """Entry with absolute path should be stale when its file is under a scanned subdir."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("x = 1  # noqa\n")
    registry_path = tmp_path / "shamefile.yaml"

    # Create registry with a stale absolute-path entry under src/
    data = {
        "config": {},
        "entries": [
            {
                "location": "src/a.py:1",
                "token": "# noqa",
                "shame_vector": "sv1:0000000000000000",
                "owner": "Test <test@test.com>",
                "created_at": "2026-01-01T00:00:00Z",
                "why": "Valid",
            },
            {
                "location": f"{tmp_path}/src/deleted.py:1",
                "token": "# noqa",
                "shame_vector": "sv1:0000000000000000",
                "owner": "Test <test@test.com>",
                "created_at": "2026-01-01T00:00:00Z",
                "why": "Should be removed",
            },
        ],
    }
    registry_path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))

    result = subprocess.run(
        [BINARY_PATH, "me", "src"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    entries = yaml.safe_load(registry_path.read_text())["entries"]
    locations = [e["location"] for e in entries]
    assert "src/a.py:1" in locations
    assert not any("deleted.py" in loc for loc in locations), (
        "Absolute-path entry under scanned subdir should be removed as stale"
    )
    assert "Removing stale entry" in result.stdout
