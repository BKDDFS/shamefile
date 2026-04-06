import pytest
import yaml

from conftest import run_shamefile

XFAIL_MATCHING = "shame_vector and cascade matching not yet implemented"


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


@pytest.mark.xfail(reason=XFAIL_MATCHING)
def test_file_rename_preserves_why(tmp_path):
    """Renaming a file should preserve why (content hash matches across files)."""
    test_file = tmp_path / "utils.py"
    test_file.write_text("x = 1  # noqa\n")
    registry_path = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Legacy code'"))
    test_file.rename(tmp_path / "helpers.py")

    run_shamefile(str(tmp_path))

    registry = yaml.safe_load(registry_path.read_text())
    entry = registry["entries"][0]

    assert entry["why"] == "Legacy code"
    assert "helpers.py" in entry["location"]


@pytest.mark.xfail(reason=XFAIL_MATCHING)
def test_file_rename_plus_content_change_reports_unmatched(tmp_path):
    """Renaming file + changing content = unmatched, tool should not auto-remove."""
    test_file = tmp_path / "utils.py"
    test_file.write_text("x = 1  # noqa\n")
    registry_path = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Legacy code'"))
    test_file.unlink()
    (tmp_path / "helpers.py").write_text("y = calculate()  # noqa\n")

    result = run_shamefile(str(tmp_path))

    # Old entry should NOT be auto-removed
    registry = yaml.safe_load(registry_path.read_text())
    assert any(e["why"] == "Legacy code" for e in registry["entries"])
    assert "algorithmic matching failed" in result.stdout
