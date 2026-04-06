from conftest import run_shamefile


def test_corrupt_yaml_exits_with_error(tmp_path):
    """Corrupt shamefile.yaml should exit 1 with error message, not panic."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    (tmp_path / "shamefile.yaml").write_text("asdkjhasd{{{")

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1
    assert "Failed to load registry" in result.stderr
    assert "Failed to parse" in result.stderr


def test_file_path_rejected(tmp_path):
    """Passing a file instead of directory should fail with clear error."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    result = run_shamefile(str(test_file))

    assert result.returncode == 1
    assert "must be a directory" in result.stderr


def test_nonexistent_directory(tmp_path):
    """Passing a non-existent directory should exit 1 with error."""
    result = run_shamefile(str(tmp_path / "nonexistent"))

    assert result.returncode == 1


def test_empty_shamefile_yaml(tmp_path):
    """Empty shamefile.yaml should be treated as existing registry with no entries."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    (tmp_path / "shamefile.yaml").write_text("")

    result = run_shamefile(str(tmp_path))

    # Should work — empty YAML deserializes to default registry
    assert "Found 1 suppressions" in result.stdout
    assert "New suppression detected" in result.stdout
