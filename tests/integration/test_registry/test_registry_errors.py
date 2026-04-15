from conftest import run_shamefile


def test_corrupt_yaml_exits_with_error(tmp_path):
    """Corrupt shamefile.yaml should exit 1 with error message, not panic."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    (tmp_path / "shamefile.yaml").write_text("asdkjhasd{{{")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "Failed to load registry" in result.stderr
    assert "Failed to parse" in result.stderr


def test_nonexistent_directory(tmp_path):
    """Passing a non-existent directory should exit 1 with error."""
    result = run_shamefile(tmp_path, "nonexistent")

    assert result.returncode == 1


def test_empty_shamefile_yaml(tmp_path):
    """Empty shamefile.yaml should be treated as existing registry with no entries."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    (tmp_path / "shamefile.yaml").write_text("")

    result = run_shamefile(tmp_path)

    # Should work — empty YAML deserializes to default registry
    assert "1 suppressions need documentation" in result.stdout
    assert "Added" in result.stdout


def test_readonly_shamefile_shows_save_error(tmp_path):
    """Read-only shamefile.yaml should produce 'save' error, not 'read' error."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"
    registry.write_text("config: {}\nentries: []\n")
    registry.chmod(0o444)

    try:
        result = run_shamefile(tmp_path)

        assert result.returncode != 0
        assert "read" not in result.stderr.lower()
        assert "save" in result.stderr.lower() or "permission" in result.stderr.lower()
    finally:
        registry.chmod(0o644)
