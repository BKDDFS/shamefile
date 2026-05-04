import subprocess

import yaml
from conftest import git_commit, git_init, run_shamefile


def test_same_content_produces_same_content(tmp_path):
    """Two entries with identical line content should have the same content."""
    (tmp_path / "a.py").write_text("x = 1  # noqa\n")
    (tmp_path / "b.py").write_text("x = 1  # noqa\n")

    run_shamefile(tmp_path)

    entries = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())["entries"]
    vectors = [e["content"] for e in entries]
    assert vectors[0] == vectors[1]


def test_different_content_produces_different_content(tmp_path):
    """Two entries with different line content should have different contents."""
    (tmp_path / "a.py").write_text("x = 1  # noqa\n")
    (tmp_path / "b.py").write_text("y = calculate()  # noqa\n")

    run_shamefile(tmp_path)

    entries = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())["entries"]
    vectors = [e["content"] for e in entries]
    assert vectors[0] != vectors[1]


def test_content_change_preserves_owner(tmp_path):
    """Changing line content on the same line should preserve owner."""
    git_init(tmp_path)
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    git_commit(tmp_path, "initial")

    run_shamefile(tmp_path)
    registry_path = tmp_path / "shamefile.yaml"
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    original = yaml.safe_load(registry_path.read_text())["entries"][0]

    # Switch to Bob
    subprocess.run(
        ["git", "config", "user.name", "Bob"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "bob@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    # Change content but keep suppression on same line
    test_file.write_text("y = calculate()  # noqa\n")
    run_shamefile(tmp_path)

    entry = yaml.safe_load(registry_path.read_text())["entries"][0]
    assert entry["owner"] == original["owner"]


def test_content_change_preserves_created_at(tmp_path):
    """Changing line content on the same line should preserve created_at."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry_path = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    original = yaml.safe_load(registry_path.read_text())["entries"][0]

    test_file.write_text("y = calculate()  # noqa\n")
    run_shamefile(tmp_path)

    entry = yaml.safe_load(registry_path.read_text())["entries"][0]
    assert entry["created_at"] == original["created_at"]


def test_rerun_without_changes_preserves_content(tmp_path):
    """Running twice without code changes should not alter content."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    registry_path = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    first = yaml.safe_load(registry_path.read_text())["entries"][0]["content"]

    run_shamefile(tmp_path)

    second = yaml.safe_load(registry_path.read_text())["entries"][0]["content"]
    assert first == second


def test_shift_plus_new_entry_on_old_line(tmp_path):
    """Token shifts to line 3, new token appears on line 1 — both should be tracked correctly."""
    git_init(tmp_path)
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    git_commit(tmp_path, "initial")

    run_shamefile(tmp_path)
    registry_path = tmp_path / "shamefile.yaml"
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Original entry'"))

    original = yaml.safe_load(registry_path.read_text())["entries"][0]

    # Shift old suppression down, add a new one on line 1
    test_file.write_text("y = 2  # type: ignore\n\nx = 1  # noqa\n")
    run_shamefile(tmp_path)

    entries = yaml.safe_load(registry_path.read_text())["entries"]
    noqa_entry = next(e for e in entries if e["token"] == "# noqa")  # noqa: S105
    type_ignore_entry = next(e for e in entries if e["token"] == "# type: ignore")  # noqa: S105

    # Old entry should preserve why via content_hash match
    assert noqa_entry["why"] == "Original entry"
    assert noqa_entry["owner"] == original["owner"]
    assert noqa_entry["created_at"] == original["created_at"]

    assert type_ignore_entry["why"] == ""
