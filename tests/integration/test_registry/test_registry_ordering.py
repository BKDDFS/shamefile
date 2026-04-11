import yaml
from conftest import run_shamefile


def make_entry(location, token="# noqa", why="", owner="Test <test@test.com>"):  # noqa: S107
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

    run_shamefile(tmp_path)

    entries = yaml.safe_load(registry.read_text())["entries"]
    assert "a.py" in entries[0]["location"]
    assert "z.py" in entries[1]["location"]


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

    run_shamefile(tmp_path)

    entries = yaml.safe_load(registry.read_text())["entries"]
    assert entries[0]["location"].endswith(":1")
    assert entries[1]["location"].endswith(":3")


def test_unsorted_tokens_get_sorted_on_same_line(tmp_path):
    """Multiple tokens on same line should be sorted alphabetically by token."""
    (tmp_path / "test.py").write_text("x = 1  # type: ignore  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # Manually create registry with # type: ignore before
    write_registry(
        registry,
        [
            make_entry(
                f"{tmp_path}/test.py:1", token="# type: ignore", why="reason ti"  # noqa: S106
            ),
            make_entry(f"{tmp_path}/test.py:1", token="# noqa", why="reason noqa"),  # noqa: S106
        ],
    )

    run_shamefile(tmp_path)

    entries = yaml.safe_load(registry.read_text())["entries"]
    tokens = [e["token"] for e in entries]
    assert tokens == sorted(tokens)


def test_new_entry_inserted_in_sorted_position(tmp_path):
    """New entry should appear in sorted position, not appended at end."""
    (tmp_path / "a.py").write_text("x = 1  # noqa\n")
    (tmp_path / "b.py").write_text("x = 1  # noqa\n")
    (tmp_path / "z.py").write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # Registry has only b.py and z.py — a.py is new
    write_registry(
        registry,
        [
            make_entry(f"{tmp_path}/b.py:1", why="reason b"),
            make_entry(f"{tmp_path}/z.py:1", why="reason z"),
        ],
    )

    run_shamefile(tmp_path)

    entries = yaml.safe_load(registry.read_text())["entries"]
    basenames = [e["location"].split("/")[-1] for e in entries]
    assert basenames[0] == "a.py:1"


def test_ordering_preserved_after_stale_removal(tmp_path):
    """After stale removal, remaining entries should still be sorted."""
    (tmp_path / "a.py").write_text("x = 1  # noqa\n")
    (tmp_path / "z.py").write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # Registry has z.py, m.py (stale), a.py — wrong order
    write_registry(
        registry,
        [
            make_entry(f"{tmp_path}/z.py:1", why="reason z"),
            make_entry(f"{tmp_path}/m.py:1", why="reason m"),
            make_entry(f"{tmp_path}/a.py:1", why="reason a"),
        ],
    )

    run_shamefile(tmp_path)

    entries = yaml.safe_load(registry.read_text())["entries"]
    assert len(entries) == 2
    assert "a.py" in entries[0]["location"]
    assert "z.py" in entries[1]["location"]


def test_ordering_stable_across_reruns(tmp_path):
    """Running shame me twice without changes should produce entries in the same order."""
    (tmp_path / "c.py").write_text("x = 1  # noqa\n")
    (tmp_path / "a.py").write_text("x = 1  # type: ignore\n")
    (tmp_path / "b.py").write_text("x = 1  # nosec\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)
    first = [e["location"] for e in yaml.safe_load(registry.read_text())["entries"]]

    run_shamefile(tmp_path)
    second = [e["location"] for e in yaml.safe_load(registry.read_text())["entries"]]

    assert first == second
