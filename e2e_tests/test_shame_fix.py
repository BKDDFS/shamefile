import yaml
from conftest import run_shame_fix, run_shamefile

CLAP_USAGE_EXIT_CODE = 2

FIVE_SUPPRESSIONS = (
    "a = 1  # noqa\nb = 2  # type: ignore\nc = 3  # nosec\n"
    "d = 4  # pragma: no cover\ne = 5  # fmt: off\n"
)


def test_fix_documents_specific_entry(tmp_path):
    """Shame fix should document the entry matching location and token."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    run_shamefile(tmp_path)

    result = run_shame_fix(tmp_path, "./test.py:2", "# type: ignore", "--why", "Third-party lib")

    assert result.returncode == 0
    assert "Documented" in result.stdout
    entries = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())["entries"]
    type_ignore = next(e for e in entries if e["token"] == "# type: ignore")  # noqa: S105
    assert type_ignore["why"] == "Third-party lib"


def test_fix_does_not_touch_other_entries(tmp_path):
    """Shame fix should only modify the targeted entry."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    run_shamefile(tmp_path)

    run_shame_fix(tmp_path, "./test.py:2", "# type: ignore", "--why", "Third-party lib")

    entries = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())["entries"]
    noqa = next(e for e in entries if e["token"] == "# noqa")  # noqa: S105
    assert noqa["why"] == ""


def test_fix_overwrites_existing_why(tmp_path):
    """Shame fix should overwrite an already documented entry."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    registry = tmp_path / "shamefile.yaml"
    run_shamefile(tmp_path)
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Old reason'"))

    result = run_shame_fix(tmp_path, "./test.py:1", "# noqa", "--why", "New reason")

    assert result.returncode == 0
    entry = yaml.safe_load(registry.read_text())["entries"][0]
    assert entry["why"] == "New reason"


def test_fix_wrong_location_fails(tmp_path):
    """Shame fix with non-existent location should fail."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    run_shamefile(tmp_path)

    result = run_shame_fix(tmp_path, "./nonexistent.py:1", "# noqa", "--why", "reason")

    assert result.returncode == 1
    assert "No entry found" in result.stderr


def test_fix_wrong_token_fails(tmp_path):
    """Shame fix with wrong token should fail."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    run_shamefile(tmp_path)

    result = run_shame_fix(tmp_path, "./test.py:1", "# type: ignore", "--why", "reason")

    assert result.returncode == 1
    assert "No entry found" in result.stderr


def test_fix_missing_why_flag_fails(tmp_path):
    """Shame fix without --why should fail with clap error."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    run_shamefile(tmp_path)

    result = run_shame_fix(tmp_path, "./test.py:1", "# noqa")

    assert result.returncode == CLAP_USAGE_EXIT_CODE


def test_fix_rejects_empty_why(tmp_path):
    """Shame fix with empty --why should fail before touching the registry."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    run_shamefile(tmp_path)

    result = run_shame_fix(tmp_path, "./test.py:1", "# noqa", "--why", "")

    assert result.returncode == 1
    assert "cannot be empty" in result.stderr


def test_fix_rejects_whitespace_only_why(tmp_path):
    """Shame fix with whitespace-only --why should fail."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    run_shamefile(tmp_path)

    result = run_shame_fix(tmp_path, "./test.py:1", "# noqa", "--why", "   \t")

    assert result.returncode == 1
    assert "cannot be empty" in result.stderr


def test_fix_no_registry(tmp_path):
    """Shame fix without registry should fail with helpful message."""
    result = run_shame_fix(tmp_path, "./test.py:1", "# noqa", "--why", "reason")

    assert result.returncode == 1
    assert "Registry not found" in result.stderr


def test_fix_shows_remaining_count(tmp_path):
    """Shame fix should show correct remaining count."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS)
    run_shamefile(tmp_path)

    run_shame_fix(tmp_path, "./test.py:1", "# noqa", "--why", "reason 1")
    result = run_shame_fix(tmp_path, "./test.py:2", "# type: ignore", "--why", "reason 2")

    assert "3 entries remaining" in result.stdout


def test_fix_last_entry_shows_all_documented(tmp_path):
    """Shame fix on the last undocumented entry should report all done."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    run_shamefile(tmp_path)

    result = run_shame_fix(tmp_path, "./test.py:1", "# noqa", "--why", "reason")

    assert "All entries documented" in result.stdout
