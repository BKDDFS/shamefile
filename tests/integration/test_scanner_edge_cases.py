import yaml

from conftest import run_shamefile


def test_binary_file_does_not_crash(tmp_path):
    """Shamefile should not crash when encountering a binary file with null bytes."""
    (tmp_path / "binary.py").write_bytes(b"\x00\x01\x02# noqa\x00\x03")
    (tmp_path / "text.py").write_text("x = 1  # noqa\n")

    result = run_shamefile(tmp_path)

    assert result.returncode < 128, "process killed by signal"
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    assert any("text.py" in e["location"] for e in registry["entries"])
