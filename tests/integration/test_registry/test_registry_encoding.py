import yaml

from conftest import run_shamefile


def test_utf8_bom_file_detected(tmp_path):
    """Token in a file starting with UTF-8 BOM should still be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_bytes(b"\xef\xbb\xbfx = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))

    entries = yaml.safe_load(registry.read_text())["entries"]
    assert len(entries) == 1
    assert entries[0]["token"] == "# noqa"


def test_crlf_line_endings_detected(tmp_path):
    """Token in a file with CRLF line endings should be detected."""
    test_file = tmp_path / "test.py"
    test_file.write_bytes(b"x = 1  # noqa\r\ny = 2\r\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))

    entries = yaml.safe_load(registry.read_text())["entries"]
    assert len(entries) == 1
    assert entries[0]["token"] == "# noqa"
