import yaml
from conftest import git_commit, git_init, run_shamefile


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


def test_same_content_different_file_no_rename_creates_new_entry(tmp_path):
    """Same content in a new file (not a rename) should not preserve why from old file."""
    git_init(tmp_path)
    (tmp_path / "utils.py").write_text("x = 1  # noqa\n")
    git_commit(tmp_path, "initial")

    run_shamefile(tmp_path)
    registry_path = tmp_path / "shamefile.yaml"
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Legacy code'"))
    git_commit(tmp_path, "add shamefile")

    # Developer adds a new file with identical content — NOT a rename, utils.py still exists
    (tmp_path / "helpers.py").write_text("x = 1  # noqa\n")
    git_commit(tmp_path, "add helpers")

    run_shamefile(tmp_path)

    registry = yaml.safe_load(registry_path.read_text())
    entries = registry["entries"]
    helpers_entry = next(e for e in entries if "helpers.py" in e["location"])
    utils_entry = next(e for e in entries if "utils.py" in e["location"])

    # Old entry keeps its why
    assert utils_entry["why"] == "Legacy code"
    # New file = new entry, must not inherit why from utils.py
    assert helpers_entry["why"] == ""


def test_deleted_file_same_line_in_unrelated_new_file_no_match(tmp_path):
    """Unrelated new file sharing one suppression line should not inherit why."""
    git_init(tmp_path)
    # utils.py has one suppression among many lines
    utils_content = "\n".join([f"line_{i} = {i}" for i in range(50)]) + "\nx = 1  # noqa\n"
    (tmp_path / "utils.py").write_text(utils_content)
    git_commit(tmp_path, "initial")

    run_shamefile(tmp_path)
    registry_path = tmp_path / "shamefile.yaml"
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Legacy code'"))
    git_commit(tmp_path, "add shamefile")

    # Delete utils.py, add different helpers.py with same suppression line
    (tmp_path / "utils.py").unlink()
    helpers_content = "\n".join([f"other_{i} = {i}" for i in range(50)]) + "\nx = 1  # noqa\n"
    (tmp_path / "helpers.py").write_text(helpers_content)
    git_commit(tmp_path, "delete utils, add helpers")

    run_shamefile(tmp_path)

    registry = yaml.safe_load(registry_path.read_text())
    entries = registry["entries"]
    helpers_entry = next(e for e in entries if "helpers.py" in e["location"])

    # Different file, git does not see rename (low similarity) — new entry, no inherited why
    assert helpers_entry["why"] == ""


def _make_realistic_file(suppression_line):
    """Build a multi-line Python file with a suppression in the middle."""
    before = "\n".join([f"line_{i} = {i}" for i in range(10)])
    after = "\n".join([f"line_{i} = {i}" for i in range(10, 20)])
    return f"{before}\n{suppression_line}\n{after}\n"


def _setup_rename_test(tmp_path, suppression_line="x = 1  # noqa"):
    """Create git repo with utils.py, run shamefile, fill why, commit."""
    git_init(tmp_path)
    test_file = tmp_path / "utils.py"
    test_file.write_text(_make_realistic_file(suppression_line))
    git_commit(tmp_path, "initial")

    run_shamefile(tmp_path)
    registry_path = tmp_path / "shamefile.yaml"
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Legacy code'"))
    git_commit(tmp_path, "add shamefile")
    return test_file, registry_path


def test_file_rename_preserves_why(tmp_path):
    """Renaming a file should preserve why (rename detection via git diff --name-status -M)."""
    test_file, registry_path = _setup_rename_test(tmp_path)

    test_file.rename(tmp_path / "helpers.py")
    git_commit(tmp_path, "rename utils to helpers")

    run_shamefile(tmp_path)

    registry = yaml.safe_load(registry_path.read_text())
    entry = registry["entries"][0]

    assert entry["why"] == "Legacy code"
    assert "helpers.py" in entry["location"]


def test_file_rename_plus_content_change_reports_unmatched(tmp_path):
    """Renaming file + changing suppression line = unmatched, should not auto-remove."""
    test_file, registry_path = _setup_rename_test(tmp_path)

    # Rename + change only the suppression line (surrounding code keeps git similarity high)
    test_file.unlink()
    (tmp_path / "helpers.py").write_text(_make_realistic_file("y = calculate()  # noqa"))
    git_commit(tmp_path, "rename and change content")

    result = run_shamefile(tmp_path)

    # Old entry should NOT be auto-removed
    registry = yaml.safe_load(registry_path.read_text())
    assert any(e["why"] == "Legacy code" for e in registry["entries"])
    assert "algorithmic matching failed" in result.stdout
    assert result.returncode == 1
