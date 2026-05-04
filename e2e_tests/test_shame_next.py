import subprocess

import yaml
from conftest import BINARY_PATH, run_shame_next, run_shamefile

FIVE_SUPPRESSIONS = (
    "a = 1  # noqa\nb = 2  # type: ignore\nc = 3  # nosec\n"
    "d = 4  # pragma: no cover\ne = 5  # fmt: off\n"
)


def test_next_shows_first_undocumented(tmp_path):
    """Shame next should display the first entry with empty why."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    run_shamefile(tmp_path)

    result = run_shame_next(tmp_path)

    assert result.returncode == 0
    assert "./test.py:1" in result.stdout
    assert "# noqa" in result.stdout


def test_next_snippet_format(tmp_path):
    """Shame next should show correctly formatted snippet."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    run_shamefile(tmp_path)

    result = run_shame_next(tmp_path)

    lines = result.stdout.strip().splitlines()
    assert lines[0] == "./test.py:1"
    assert lines[1] == "    |"
    assert lines[2] == "   1| a = 1  # noqa"
    assert lines[3] == "    |        ^^^^^^"


def test_next_shows_fix_hint(tmp_path):
    """Shame next should show both fix commands."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    run_shamefile(tmp_path)

    result = run_shame_next(tmp_path)

    assert 'shame next "<reason>"' in result.stdout
    assert 'shame fix "./test.py:1" "# noqa" --why "<reason>"' in result.stdout


def test_next_all_documented(tmp_path):
    """Shame next when all entries have why should report nothing to do."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    registry = tmp_path / "shamefile.yaml"
    run_shamefile(tmp_path)
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Justified'"))

    result = run_shame_next(tmp_path)

    assert result.returncode == 0
    assert "No entries need documentation" in result.stdout


def test_next_no_registry(tmp_path):
    """Shame next without registry should fail with helpful message."""
    result = run_shame_next(tmp_path)

    assert result.returncode == 1
    assert "Registry not found" in result.stderr


def test_next_snippet_handles_missing_source_file(tmp_path):
    """Shame next should print location only when entry's source file is gone."""
    registry = tmp_path / "shamefile.yaml"
    registry.write_text(
        "---\n"
        "config: {}\n"
        "entries:\n"
        "  - location: ./gone.py:1\n"
        "    token: '# noqa'\n"
        "    content: 'x = 1  # noqa'\n"
        "    created_at: '2024-01-15T00:00:00Z'\n"
        "    owner: alice\n"
        "    why: ''\n"
    )

    result = run_shame_next(tmp_path)

    assert result.returncode == 0
    assert "./gone.py:1" in result.stdout
    # No snippet rendered because source file does not exist.
    assert "    |" not in result.stdout


def test_next_snippet_handles_line_beyond_eof(tmp_path):
    """Shame next should skip the snippet body when the line is past EOF."""
    (tmp_path / "short.py").write_text("only_one_line = 1\n")
    registry = tmp_path / "shamefile.yaml"
    registry.write_text(
        "---\n"
        "config: {}\n"
        "entries:\n"
        "  - location: ./short.py:99\n"
        "    token: '# noqa'\n"
        "    content: 'x'\n"
        "    created_at: '2024-01-15T00:00:00Z'\n"
        "    owner: alice\n"
        "    why: ''\n"
    )

    result = run_shame_next(tmp_path)

    assert result.returncode == 0
    assert "./short.py:99" in result.stdout
    assert "    |" not in result.stdout


def test_next_with_reason_documents_entry(tmp_path):
    """Shame next with reason should fill the why field."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    run_shamefile(tmp_path)

    subprocess.run(
        [BINARY_PATH, "next", "Legacy API"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    entry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())["entries"][0]
    assert entry["why"] == "Legacy API"


def test_next_with_reason_targets_same_entry_as_next(tmp_path):
    """Shame next and shame next 'reason' must target the exact same entry."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    run_shamefile(tmp_path)

    # shame next shows first entry: ./test.py:1 with noqa token
    show_result = run_shame_next(tmp_path)
    assert "./test.py:1" in show_result.stdout
    assert "# noqa" in show_result.stdout

    # shame next "reason" must fix that same ./test.py:1 noqa entry
    fix_result = subprocess.run(
        [BINARY_PATH, "next", "First reason"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    assert "Documented: # noqa at ./test.py:1" in fix_result.stdout

    # Verify in YAML: first entry has why, rest untouched
    entries = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())["entries"]
    assert entries[0]["location"] == "./test.py:1"
    assert entries[0]["token"] == "# noqa"  # noqa: S105
    assert entries[0]["why"] == "First reason"
    for entry in entries[1:]:
        assert entry["why"] == ""


def test_next_with_reason_shows_next_entry(tmp_path):
    """Shame next with reason should show the next undocumented entry after fixing."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    run_shamefile(tmp_path)

    result = subprocess.run(
        [BINARY_PATH, "next", "Legacy API"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert "Documented: # noqa" in result.stdout
    assert "./test.py:2" in result.stdout
    assert "# type: ignore" in result.stdout


def test_next_with_reason_does_not_show_fixed_snippet(tmp_path):
    """Shame next with reason should not show snippet for the entry it just fixed."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    run_shamefile(tmp_path)

    result = subprocess.run(
        [BINARY_PATH, "next", "Legacy API"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert "   1| a = 1" not in result.stdout


def test_next_with_reason_last_entry(tmp_path):
    """Shame next with reason on last entry should report all documented."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    run_shamefile(tmp_path)

    result = subprocess.run(
        [BINARY_PATH, "next", "Legacy API"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert "Documented" in result.stdout
    assert "All entries documented" in result.stdout


def test_next_with_reason_no_registry(tmp_path):
    """Shame next with reason without registry should fail."""
    result = subprocess.run(
        [BINARY_PATH, "next", "some reason"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 1
    assert "Registry not found" in result.stderr


def test_next_with_reason_advances_queue(tmp_path):
    """Repeated shame next with reason should advance through all entries in order."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    run_shamefile(tmp_path)

    reasons = ["Reason 1", "Reason 2", "Reason 3", "Reason 4", "Reason 5"]
    for reason in reasons:
        subprocess.run(
            [BINARY_PATH, "next", reason],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            check=False,
        )

    entries = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())["entries"]
    for i, reason in enumerate(reasons):
        assert entries[i]["why"] == reason


# Reason content tests (apostrophe, colons, hashes, unicode, YAML keywords, numbers, URLs,
# double quotes, percent) live in e2e_tests/test_yaml_formatting.py (BDD).


def test_next_rejects_empty_reason(tmp_path):
    """Shame next with empty string should fail, not write empty why."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    run_shamefile(tmp_path)

    result = subprocess.run(
        [BINARY_PATH, "next", ""],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 1
    entry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())["entries"][0]
    assert entry["why"] == ""


def test_next_rejects_whitespace_only_reason(tmp_path):
    """Shame next with whitespace-only reason should fail."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    run_shamefile(tmp_path)

    result = subprocess.run(
        [BINARY_PATH, "next", "   "],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 1
    entry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())["entries"][0]
    assert entry["why"] == ""
