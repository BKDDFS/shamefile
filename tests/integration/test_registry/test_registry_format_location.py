import yaml

from conftest import run_shamefile


def test_entry_location_matches_line_position(tmp_path):
    """Location line number should match actual position in file."""
    test_file = tmp_path / "test.py"
    test_file.write_text("clean\nclean\nx = 1  # noqa\n")

    run_shamefile(tmp_path)

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]

    assert entry["location"].endswith("test.py:3")


def test_entry_location_includes_nested_path(tmp_path):
    """Location should include full path for files in subdirectories."""
    nested = tmp_path / "src" / "deep"
    nested.mkdir(parents=True)
    test_file = nested / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile(tmp_path)

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]

    assert "src/deep/test.py:1" in entry["location"]


def test_entry_location_with_spaces_in_path(tmp_path):
    """Location should handle spaces in directory and file names."""
    spaced = tmp_path / "my project" / "sub dir"
    spaced.mkdir(parents=True)
    test_file = spaced / "my file.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile(tmp_path)

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]

    assert "my project/sub dir/my file.py:1" in entry["location"]


def test_entry_location_with_colon_in_path(tmp_path):
    """Location should handle colons in directory names (rsplit_once splits on last colon)."""
    colon_dir = tmp_path / "src" / "foo:bar"
    colon_dir.mkdir(parents=True)
    test_file = colon_dir / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile(tmp_path)

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entry = registry["entries"][0]

    assert "src/foo:bar/test.py:1" in entry["location"]
