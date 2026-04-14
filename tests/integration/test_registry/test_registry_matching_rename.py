import pytest
import yaml
from conftest import git_commit, git_init, run_shamefile

XFAIL_RENAME = "rename detection (git diff --name-status -M) not yet implemented"


def test_content_change_updates_shame_vector(tmp_path):
    """Changing line content should update shame_vector hash while preserving why."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry_path = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    original = yaml.safe_load(registry_path.read_text())["entries"][0]

    # Developer changes the code but keeps the suppression on the same line
    test_file.write_text("y = calculate()  # noqa\n")

    run_shamefile(tmp_path)

    registry = yaml.safe_load(registry_path.read_text())
    entry = registry["entries"][0]

    assert entry["why"] == "Legacy code"
    assert "shame_vector" in entry
    assert entry["shame_vector"] != original.get("shame_vector")


def test_line_shift_and_content_change_reports_unmatched(tmp_path):
    """Line shift + content change = unmatched, tool should not auto-remove."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry_path = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    # Developer changes both line and content
    test_file.write_text("\ny = calculate()  # noqa\n")

    result = run_shamefile(tmp_path)

    # Old entry should NOT be auto-removed
    registry = yaml.safe_load(registry_path.read_text())
    assert any(e["why"] == "Legacy code" for e in registry["entries"])
    assert "algorithmic matching failed" in result.stdout
    assert result.returncode == 1


@pytest.mark.xfail(reason=XFAIL_RENAME)
def test_file_rename_preserves_why(tmp_path):
    """Renaming a file should preserve why (rename detection via git diff --name-status -M)."""
    git_init(tmp_path)
    test_file = tmp_path / "utils.py"
    test_file.write_text("x = 1  # noqa\n")
    git_commit(tmp_path, "initial")

    run_shamefile(tmp_path)
    registry_path = tmp_path / "shamefile.yaml"
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Legacy code'"))
    git_commit(tmp_path, "add shamefile")

    # Rename via git mv so git tracks the rename
    test_file.rename(tmp_path / "helpers.py")
    git_commit(tmp_path, "rename utils to helpers")

    run_shamefile(tmp_path)

    registry = yaml.safe_load(registry_path.read_text())
    entry = registry["entries"][0]

    assert entry["why"] == "Legacy code"
    assert "helpers.py" in entry["location"]


@pytest.mark.xfail(reason=XFAIL_RENAME)
def test_file_rename_plus_content_change_reports_unmatched(tmp_path):
    """Renaming file + changing content = unmatched, tool should not auto-remove."""
    git_init(tmp_path)
    test_file = tmp_path / "utils.py"
    test_file.write_text("x = 1  # noqa\n")
    git_commit(tmp_path, "initial")

    run_shamefile(tmp_path)
    registry_path = tmp_path / "shamefile.yaml"
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Legacy code'"))
    git_commit(tmp_path, "add shamefile")

    # Rename + change content
    test_file.unlink()
    (tmp_path / "helpers.py").write_text("y = calculate()  # noqa\n")
    git_commit(tmp_path, "rename and change content")

    result = run_shamefile(tmp_path)

    # Old entry should NOT be auto-removed
    registry = yaml.safe_load(registry_path.read_text())
    assert any(e["why"] == "Legacy code" for e in registry["entries"])
    assert "algorithmic matching failed" in result.stdout
    assert result.returncode == 1
