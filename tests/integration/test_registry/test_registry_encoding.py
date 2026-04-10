import yaml

from conftest import run_shamefile


def test_utf8_bom_file_detected(tmp_path):
    """Token in a file starting with UTF-8 BOM should still be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_bytes(b"\xef\xbb\xbfx = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)

    entries = yaml.safe_load(registry.read_text())["entries"]
    assert len(entries) == 1
    assert entries[0]["token"] == "# noqa"


def test_crlf_line_endings_detected(tmp_path):
    """Token in a file with CRLF line endings should be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_bytes(b"x = 1  # noqa\r\ny = 2\r\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)

    entries = yaml.safe_load(registry.read_text())["entries"]
    assert len(entries) == 1
    assert entries[0]["token"] == "# noqa"


def test_non_utf8_file_skipped_with_warning(tmp_path):
    """File with non-UTF-8 bytes should be skipped with a warning, not crash the scanner."""
    # Latin-1 encoded file with é (0xe9) which is invalid UTF-8
    non_utf8 = tmp_path / "legacy.py"
    non_utf8.write_bytes(b"x = 1  # obej\xe9cie  # noqa\n")

    # Also add a valid file to confirm scanning continues
    valid = tmp_path / "valid.py"
    valid.write_text("y = 2  # type: ignore\n")
    registry = tmp_path / "shamefile.yaml"

    result = run_shamefile(tmp_path)

    # Scanner should warn about the skipped file
    assert "Warning" in result.stderr
    assert "legacy.py" in result.stderr

    # Valid file should still be detected
    entries = yaml.safe_load(registry.read_text())["entries"]
    valid_tokens = [e["token"] for e in entries]
    assert "# type: ignore" in valid_tokens
