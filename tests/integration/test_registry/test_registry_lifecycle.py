from conftest import run_shamefile


def test_happy_path_all_justified(tmp_path):
    """All suppressions justified — exit 0, no errors."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 0
    assert "Validation passed" in result.stdout


def test_empty_why_fails(tmp_path):
    """Entry with empty 'why' should cause exit code 1."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1
    assert "Missing reason (why)" in result.stdout


def test_whitespace_only_why_is_rejected(tmp_path):
    """Entry with whitespace-only 'why' should be treated as empty."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: '   '"))

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1
    assert "Missing reason (why)" in result.stdout


def test_creates_registry_when_missing(tmp_path):
    """Running shame me on a dir without shamefile.yaml should create it."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"
    assert not registry.exists()

    result = run_shamefile(str(tmp_path))

    assert registry.exists()
    assert result.returncode == 1


def test_no_suppressions_creates_empty_registry(tmp_path):
    """Clean code with no suppressions should create empty registry and exit 0."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1\n")
    registry = tmp_path / "shamefile.yaml"

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 0
    assert registry.exists()
    assert "Found 0 suppressions" in result.stdout
