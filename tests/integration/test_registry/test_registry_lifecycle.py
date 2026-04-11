import subprocess

import yaml
from conftest import run_shamefile


def test_happy_path_all_justified(tmp_path):
    """All suppressions justified — exit 0, no errors."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    assert "Validation passed" in result.stdout


def test_empty_why_fails(tmp_path):
    """Entry with empty 'why' should cause exit code 1."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "Missing reason (why)" in result.stdout


def test_whitespace_only_why_is_rejected(tmp_path):
    """Entry with whitespace-only 'why' should be treated as empty."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: '   '"))

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "Missing reason (why)" in result.stdout


def test_whitespace_wrapped_why_is_accepted(tmp_path):
    """Entry with whitespace-wrapped real content in 'why' should pass validation."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: '  Legacy code  '"))

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    assert "Validation passed" in result.stdout


def test_newline_only_why_is_rejected(tmp_path):
    """Entry with newline-only 'why' should be treated as empty."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", 'why: "\\n\\n"'))

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "Missing reason (why)" in result.stdout


def test_creates_registry_when_missing(tmp_path):
    """Running shame me on a dir without shamefile.yaml should create it."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"
    assert not registry.exists()

    result = run_shamefile(tmp_path)

    assert registry.exists()
    assert result.returncode == 1


def test_no_suppressions_creates_empty_registry(tmp_path):
    """Clean code with no suppressions should create empty registry and exit 0."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1\n")
    registry = tmp_path / "shamefile.yaml"

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    assert registry.exists()
    assert "Found 0 suppressions" in result.stdout


def test_delete_registry_and_rerun_behaves_as_first_run(tmp_path):
    """Deleting shamefile.yaml and rerunning should behave identically to a first run."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Alice"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "alice@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )

    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True, check=True
    )

    # First run — creates registry
    run_shamefile(tmp_path)
    registry = tmp_path / "shamefile.yaml"
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    # Confirm justified → exit 0
    result = run_shamefile(tmp_path)
    assert result.returncode == 0

    # Delete registry
    registry.unlink()

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

    # Rerun — should behave as first run (blame, not current user)
    result = run_shamefile(tmp_path)

    assert "Creating new registry" in result.stdout
    assert result.returncode == 1  # empty why on fresh entry

    registry_data = yaml.safe_load(registry.read_text())
    entry = registry_data["entries"][0]
    # Blame attributes to Alice (committer), NOT Bob (current user)
    assert entry["owner"] == "Alice <alice@test.com>"
