import pytest
import yaml

from conftest import run_shamefile

XFAIL_ORDERING = "entry ordering not yet implemented"


def make_entry(location, token="# noqa", why="", owner="Test <test@test.com>"):
    """Create a minimal shamefile entry dict."""
    return {
        "location": location,
        "token": token,
        "owner": owner,
        "created_at": "2026-01-01T00:00:00Z",
        "why": why,
    }


def write_registry(path, entries):
    """Write a shamefile.yaml with given entries."""
    data = {"config": {}, "entries": entries}
    path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))


@pytest.mark.xfail(reason=XFAIL_ORDERING)
def test_unsorted_entries_get_sorted_by_file(tmp_path):
    """Entries in wrong file order should be sorted after rerun."""
    (tmp_path / "a.py").write_text("x = 1  # noqa\n")
    (tmp_path / "z.py").write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # Manually create registry with z.py before a.py
    write_registry(
        registry,
        [
            make_entry(f"{tmp_path}/z.py:1", why="reason z"),
            make_entry(f"{tmp_path}/a.py:1", why="reason a"),
        ],
    )

    run_shamefile(str(tmp_path))

    entries = yaml.safe_load(registry.read_text())["entries"]
    assert "a.py" in entries[0]["location"]
    assert "z.py" in entries[1]["location"]


@pytest.mark.xfail(reason=XFAIL_ORDERING)
def test_unsorted_lines_get_sorted_within_file(tmp_path):
    """Entries with lines in wrong order should be sorted after rerun."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\ny = 2\nz = 3  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # Manually create registry with line 3 before line 1
    write_registry(
        registry,
        [
            make_entry(f"{tmp_path}/test.py:3", why="reason 3"),
            make_entry(f"{tmp_path}/test.py:1", why="reason 1"),
        ],
    )

    run_shamefile(str(tmp_path))

    entries = yaml.safe_load(registry.read_text())["entries"]
    assert entries[0]["location"].endswith(":1")
    assert entries[1]["location"].endswith(":3")
