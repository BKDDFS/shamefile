import yaml
from conftest import run_shamefile


def make_entry(
    location,
    token="# noqa",  # noqa: S107
    why="",
    owner="Test <test@test.com>",
    shame_vector="sv1:0000000000000000",
):
    """Create a minimal shamefile entry dict."""
    return {
        "location": location,
        "token": token,
        "shame_vector": shame_vector,
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
            make_entry("z.py:1", why="reason z"),
            make_entry("a.py:1", why="reason a"),
        ],
    )

    run_shamefile(tmp_path)

    entries = yaml.safe_load(registry.read_text())["entries"]
    assert entries[0]["location"] == "a.py:1"
    assert entries[1]["location"] == "z.py:1"


def test_unsorted_lines_get_sorted_within_file(tmp_path):
    """Entries with lines in wrong order should be sorted after rerun."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\ny = 2\nz = 3  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # Manually create registry with line 3 before line 1
    write_registry(
        registry,
        [
            make_entry("test.py:3", why="reason 3"),
            make_entry("test.py:1", why="reason 1"),
        ],
    )

    run_shamefile(tmp_path)

    entries = yaml.safe_load(registry.read_text())["entries"]
    assert entries[0]["location"] == "test.py:1"
    assert entries[1]["location"] == "test.py:3"


def test_unsorted_tokens_get_sorted_on_same_line(tmp_path):
    """Multiple tokens on same line should be sorted alphabetically by token."""
    (tmp_path / "test.py").write_text("x = 1  # type: ignore  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # Manually create registry with # type: ignore before
    write_registry(
        registry,
        [
            make_entry(
                "test.py:1",
                token="# type: ignore",  # noqa: S106
                why="reason ti",
            ),
            make_entry(
                "test.py:1",
                token="# noqa",  # noqa: S106
                why="reason noqa",
            ),
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
            make_entry("b.py:1", why="reason b"),
            make_entry("z.py:1", why="reason z"),
        ],
    )

    run_shamefile(tmp_path)

    entries = yaml.safe_load(registry.read_text())["entries"]
    assert entries[0]["location"] == "a.py:1"


def test_ordering_preserved_after_stale_removal(tmp_path):
    """After file deletion, remaining entries should still be sorted."""
    (tmp_path / "a.py").write_text("x = 1  # noqa\n")
    (tmp_path / "z.py").write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # Registry has z.py, m.py (file deleted = auto-remove), a.py — wrong order
    write_registry(
        registry,
        [
            make_entry("z.py:1", why="reason z"),
            make_entry("m.py:1", why="reason m"),
            make_entry("a.py:1", why="reason a"),
        ],
    )

    run_shamefile(tmp_path)

    entries = yaml.safe_load(registry.read_text())["entries"]
    # m.py entry removed (file deleted), a.py and z.py matched and preserved
    expected_entries = 2  # a.py + z.py
    assert len(entries) == expected_entries
    assert entries[0]["location"] == "a.py:1"
    assert entries[1]["location"] == "z.py:1"


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
