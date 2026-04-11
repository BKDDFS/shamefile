import yaml
from conftest import run_shamefile


def test_existing_entry_with_why_survives_rerun(tmp_path):
    """An entry with a filled 'why' should not be lost on next run."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # First run — creates registry with empty why
    run_shamefile(tmp_path)

    # Simulate developer filling in the why
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Legacy code, see JIRA-123'"))

    # Second run — should keep the existing entry with why
    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    assert "JIRA-123" in registry.read_text()


def test_created_at_preserved_after_filling_why(tmp_path):
    """Filling in 'why' and rerunning should not change created_at."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)
    original_created_at = yaml.safe_load(registry.read_text())["entries"][0]["created_at"]

    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    run_shamefile(tmp_path)

    entry = yaml.safe_load(registry.read_text())["entries"][0]
    assert entry["created_at"] == original_created_at


def test_new_suppression_added_while_existing_preserved(tmp_path):
    """Adding new suppression to code should not lose existing justified entries."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # First run + fill why
    run_shamefile(tmp_path)
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Legacy code, see JIRA-123'"))

    # Developer adds new suppression
    test_file.write_text("x = 1  # noqa\ny = 2  # type: ignore\n")

    # Second run
    result = run_shamefile(tmp_path)

    registry_content = registry.read_text()
    assert result.returncode == 1  # new entry has empty why
    assert "JIRA-123" in registry_content  # old entry preserved
    assert "# type: ignore" in result.stdout  # new suppression detected


def test_same_token_on_multiple_lines_tracked_independently(tmp_path):
    """Same token on different lines should be separate entries with independent why."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\ny = 2  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # First run — creates two entries
    run_shamefile(tmp_path)
    content = registry.read_text()
    assert content.count("# noqa") == 2

    # Justify only the first one (line 1)
    registry.write_text(content.replace("why: ''", "why: 'Justified'", 1))

    result = run_shamefile(tmp_path)

    assert result.returncode == 1  # second entry still unjustified
    registry_content = registry.read_text()
    assert registry_content.count("# noqa") == 2  # both still tracked
    assert "Justified" in registry_content  # first entry preserved


def test_duplicate_token_on_same_line_counted_once(tmp_path):
    """Same token appearing twice on one line should be tracked as single entry."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa  # noqa\n")

    result = run_shamefile(tmp_path)

    assert "Found 1 suppressions" in result.stdout


def test_multiple_files_multiple_tokens_multiple_lines(tmp_path):
    """Different tokens across files and lines should all be tracked independently."""
    (tmp_path / "a.py").write_text(
        "x = 1  # noqa\ny = 2  # noqa\nz = 3  # type: ignore\n"
    )
    (tmp_path / "b.py").write_text("a = 1  # nosec\n")
    (tmp_path / "c.js").write_text("b = 2  // eslint-disable-line no-unused-vars\n")
    registry = tmp_path / "shamefile.yaml"

    result = run_shamefile(tmp_path)

    assert "Found 5 suppressions" in result.stdout

    # Justify only first entry
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Justified'", 1))

    result = run_shamefile(tmp_path)

    assert result.returncode == 1  # four still unjustified
    assert "Justified" in registry.read_text()


def test_noqa_prefix_not_double_counted(tmp_path):
    """A line with '# noqa: E501' should create only one entry, not two."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa: E501\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)

    entries = yaml.safe_load(registry.read_text())["entries"]
    assert len(entries) == 1


def test_suppression_on_last_line_without_trailing_newline(tmp_path):
    """Token on last line without trailing newline should still be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_bytes(b"x = 1  # noqa")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)

    entries = yaml.safe_load(registry.read_text())["entries"]
    assert len(entries) == 1
    assert entries[0]["token"] == "# noqa"


def test_different_tokens_same_line_independent_entries(tmp_path):
    """Different tokens on same line should be separate entries with independent why."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa  # type: ignore\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)

    entries = yaml.safe_load(registry.read_text())["entries"]
    tokens = {e["token"] for e in entries}

    assert len(entries) == 2
    assert "# noqa" in tokens
    assert "# type: ignore" in tokens
