import yaml
from conftest import run_shamefile


def test_unicode_in_why_preserved(tmp_path):
    """Unicode characters in why field should survive rerun without corruption."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)

    unicode_why = "Wegen Kompatibilität — José 日本語 🔥"
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", f"why: '{unicode_why}'"))

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    entry = yaml.safe_load(registry.read_text())["entries"][0]
    assert entry["why"] == unicode_why


def test_multiline_why_accepted(tmp_path):
    """Multiline why (YAML block scalar) should be treated as non-empty."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)

    # Replace why with a YAML block scalar
    content = registry.read_text()
    registry.write_text(
        content.replace(
            "why: ''",
            "why: |\n      This is a long explanation\n      spanning multiple lines",
        )
    )

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    entry = yaml.safe_load(registry.read_text())["entries"][0]
    assert "long explanation" in entry["why"]


def test_why_null_treated_as_empty(tmp_path):
    """Explicit YAML null in why field should be treated as missing justification."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)

    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: null"))

    result = run_shamefile(tmp_path)

    assert result.returncode == 1


def test_why_with_yaml_special_chars(tmp_path):
    """Why containing YAML special characters should survive rerun."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)

    special_why = 'reason: see ticket #123 & "fix"'
    data = yaml.safe_load(registry.read_text())
    data["entries"][0]["why"] = special_why
    registry.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    entry = yaml.safe_load(registry.read_text())["entries"][0]
    assert entry["why"] == special_why


def test_extra_fields_in_entry_stripped(tmp_path):
    """Unknown fields added manually to an entry are silently removed by serde on rerun."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)

    data = yaml.safe_load(registry.read_text())
    data["entries"][0]["why"] = "Legacy code"
    data["entries"][0]["ticket"] = "JIRA-123"
    data["entries"][0]["reviewer"] = "Alice"
    registry.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))

    run_shamefile(tmp_path)

    entry = yaml.safe_load(registry.read_text())["entries"][0]
    assert entry["why"] == "Legacy code"
    assert "ticket" not in entry
    assert "reviewer" not in entry


def test_missing_required_field_exits_with_error(tmp_path):
    """Missing required field (token) in entry should produce a clear deserialization error."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    (tmp_path / "shamefile.yaml").write_text(
        "config: {}\n"
        "entries:\n"
        "  - location: 'test.py:1'\n"
        "    owner: 'Alice'\n"
        "    created_at: '2024-01-15T00:00:00Z'\n"
        "    why: 'reason'\n"
    )

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "Failed to load registry" in result.stderr
    assert "missing field" in result.stderr


def test_wrong_type_in_field_exits_with_error(tmp_path):
    """Wrong type (list instead of string) in field should produce deserialization error."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    (tmp_path / "shamefile.yaml").write_text(
        "config: {}\n"
        "entries:\n"
        "  - location: 'test.py:1'\n"
        "    token: ['# noqa', '# nosec']\n"
        "    owner: 'Alice'\n"
        "    created_at: '2024-01-15T00:00:00Z'\n"
        "    why: 'reason'\n"
    )

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "Failed to load registry" in result.stderr
    assert "invalid type" in result.stderr


def test_non_utc_timezone_normalized_to_utc(tmp_path):
    """Non-UTC timezone offset in created_at is parsed and normalized to UTC by chrono."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    (tmp_path / "shamefile.yaml").write_text(
        "config: {}\n"
        "entries:\n"
        "  - location: './test.py:1'\n"
        "    token: '# noqa'\n"
        "    owner: 'Alice'\n"
        "    created_at: '2024-01-15T10:00:00+05:30'\n"
        "    why: 'Legacy'\n"
    )

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    saved = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    created_at = str(saved["entries"][0]["created_at"])
    assert "2024-01-15" in created_at
    assert "04:30" in created_at


def test_yaml_anchor_merge_key_fails_with_clear_error(tmp_path):
    """YAML merge keys (<<: *alias) are not supported by serde_yaml — should fail without panic."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\ny = 2  # type: ignore\n")
    (tmp_path / "shamefile.yaml").write_text(
        "config: {}\n"
        "entries:\n"
        "  - &base\n"
        "    location: test.py:1\n"
        "    token: '# noqa'\n"
        "    owner: Alice\n"
        "    created_at: '2024-01-15T00:00:00Z'\n"
        "    why: Legacy\n"
        "  - <<: *base\n"
        "    location: test.py:2\n"
        "    token: '# type: ignore'\n"
    )

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "Failed to load registry" in result.stderr
    assert "missing field" in result.stderr


def test_yaml_scalar_anchor_resolved(tmp_path):
    """YAML scalar anchors (&name / *name) are resolved by serde_yaml — entries load correctly."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\ny = 2  # type: ignore\n")
    (tmp_path / "shamefile.yaml").write_text(
        "config: {}\n"
        "entries:\n"
        "  - location: test.py:1\n"
        "    token: '# noqa'\n"
        "    owner: &alice Alice\n"
        "    created_at: '2024-01-15T00:00:00Z'\n"
        "    why: Legacy\n"
        "  - location: test.py:2\n"
        "    token: '# type: ignore'\n"
        "    owner: *alice\n"
        "    created_at: '2024-01-15T00:00:00Z'\n"
        "    why: Legacy\n"
    )

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    data = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    expected_entries = 2  # two tokens in file
    assert len(data["entries"]) == expected_entries
    assert data["entries"][1]["owner"] == "Alice"


def test_duplicate_entries_rejected(tmp_path):
    """Duplicate entries (same location + token) should be rejected with a clear error."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    (tmp_path / "shamefile.yaml").write_text(
        "config: {}\n"
        "entries:\n"
        "  - location: './test.py:1'\n"
        "    token: '# noqa'\n"
        "    owner: 'Alice'\n"
        "    created_at: '2024-01-15T00:00:00Z'\n"
        "    why: 'Legacy from 2019'\n"
        "  - location: './test.py:1'\n"
        "    token: '# noqa'\n"
        "    owner: 'Bob'\n"
        "    created_at: '2024-02-01T00:00:00Z'\n"
        "    why: 'Performance workaround per JIRA-456'\n"
    )

    result = run_shamefile(tmp_path)

    output = result.stderr + result.stdout
    assert result.returncode == 1
    assert "duplicate" in output.lower()
    # Token and source location help the user understand the conflict.
    assert "# noqa" in output
    assert "test.py:1" in output
    # IDE-clickable references to BOTH duplicate rows in shamefile.yaml itself.
    # Entries start at lines 3 and 8 of the fixture written above.
    assert "shamefile.yaml:3" in output
    assert "shamefile.yaml:8" in output
