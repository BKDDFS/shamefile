import subprocess

from conftest import run_shamefile


def test_stale_entry_removed(tmp_path):
    """Removing suppression from code should remove its entry from registry."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # First run — creates entry
    run_shamefile(str(tmp_path))
    assert "# noqa" in registry.read_text()

    # Developer removes suppression
    test_file.write_text("x = 1\n")

    # Second run — should remove stale entry
    result = run_shamefile(str(tmp_path))

    assert result.returncode == 0
    assert "Removing stale entry" in result.stdout
    assert "# noqa" not in registry.read_text()


def test_deleted_file_entries_become_stale(tmp_path):
    """Deleting a file with suppressions should remove its entries from registry."""
    file_a = tmp_path / "a.py"
    file_b = tmp_path / "b.py"
    file_a.write_text("x = 1  # noqa\n")
    file_b.write_text("y = 2  # type: ignore\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))
    assert "# noqa" in registry.read_text()
    assert "type: ignore" in registry.read_text()

    # Delete one file
    file_a.unlink()

    result = run_shamefile(str(tmp_path))

    registry_content = registry.read_text()
    assert "# noqa" not in registry_content
    assert "type: ignore" in registry_content
    assert "Removing stale entry" in result.stdout


def test_existing_entry_with_why_survives_rerun(tmp_path):
    """An entry with a filled 'why' should not be lost on next run."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # First run — creates registry with empty why
    run_shamefile(str(tmp_path))

    # Simulate developer filling in the why
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Legacy code, see JIRA-123'"))

    # Second run — should keep the existing entry with why
    result = run_shamefile(str(tmp_path))

    assert result.returncode == 0
    assert "JIRA-123" in registry.read_text()


def test_new_suppression_added_while_existing_preserved(tmp_path):
    """Adding new suppression to code should not lose existing justified entries."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # First run + fill why
    run_shamefile(str(tmp_path))
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Legacy code, see JIRA-123'"))

    # Developer adds new suppression
    test_file.write_text("x = 1  # noqa\ny = 2  # type: ignore\n")

    # Second run
    result = run_shamefile(str(tmp_path))

    registry_content = registry.read_text()
    assert result.returncode == 1  # new entry has empty why
    assert "JIRA-123" in registry_content  # old entry preserved
    assert "# type: ignore" in result.stdout  # new suppression detected


def test_replacing_token_removes_old_and_adds_new(tmp_path):
    """Swapping one suppression for another should remove old entry and create new one."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # First run + fill why
    run_shamefile(str(tmp_path))
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    # Developer replaces token
    test_file.write_text("x = 1  # type: ignore\n")

    result = run_shamefile(str(tmp_path))

    registry_content = registry.read_text()
    assert "# noqa" not in registry_content
    assert "# type: ignore" in registry_content
    assert "Legacy code" not in registry_content
    assert "Removing stale entry" in result.stdout
    assert "New suppression detected" in result.stdout


def test_same_token_on_multiple_lines_tracked_independently(tmp_path):
    """Same token on different lines should be separate entries with independent why."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\ny = 2  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # First run — creates two entries
    run_shamefile(str(tmp_path))
    content = registry.read_text()
    assert content.count("# noqa") == 2

    # Justify only the first one (line 1)
    registry.write_text(content.replace("why: ''", "why: 'Justified'", 1))

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1  # second entry still unjustified
    registry_content = registry.read_text()
    assert registry_content.count("# noqa") == 2  # both still tracked
    assert "Justified" in registry_content  # first entry preserved


def test_duplicate_token_on_same_line_counted_once(tmp_path):
    """Same token appearing twice on one line should be tracked as single entry."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa  # noqa\n")

    result = run_shamefile(str(tmp_path))

    assert "Found 1 suppressions" in result.stdout


def test_multiple_files_multiple_tokens_multiple_lines(tmp_path):
    """Different tokens across files and lines should all be tracked independently."""
    (tmp_path / "a.py").write_text(
        "x = 1  # noqa\ny = 2  # noqa\nz = 3  # type: ignore\n"
    )
    (tmp_path / "b.py").write_text("a = 1  # nosec\n")
    (tmp_path / "c.js").write_text("b = 2  // eslint-disable-line no-unused-vars\n")
    registry = tmp_path / "shamefile.yaml"

    result = run_shamefile(str(tmp_path))

    assert "Found 5 suppressions" in result.stdout

    # Justify only first entry
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Justified'", 1))

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1  # four still unjustified
    assert "Justified" in registry.read_text()


def test_gitignored_file_entries_become_stale(tmp_path):
    """Adding a tracked file to .gitignore should remove its entries from registry."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # Need git repo for .gitignore to work
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)

    # First run — creates entry
    run_shamefile(str(tmp_path))
    assert "# noqa" in registry.read_text()
    (tmp_path / ".gitignore").write_text("test.py\n")

    # Second run — entry should be removed as stale
    result = run_shamefile(str(tmp_path))

    assert "Removing stale entry" in result.stdout
    assert "# noqa" not in registry.read_text()
