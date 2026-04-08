import yaml

from conftest import run_shamefile


def test_unicode_in_why_preserved(tmp_path):
    """Unicode characters in why field should survive rerun without corruption."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))

    unicode_why = "Wegen Kompatibilität — José 日本語 🔥"
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", f"why: '{unicode_why}'"))

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 0
    entry = yaml.safe_load(registry.read_text())["entries"][0]
    assert entry["why"] == unicode_why


def test_multiline_why_accepted(tmp_path):
    """Multiline why (YAML block scalar) should be treated as non-empty."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))

    # Replace why with a YAML block scalar
    content = registry.read_text()
    registry.write_text(
        content.replace(
            "why: ''",
            "why: |\n      This is a long explanation\n      spanning multiple lines",
        )
    )

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 0
    entry = yaml.safe_load(registry.read_text())["entries"][0]
    assert "long explanation" in entry["why"]
