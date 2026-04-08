import pytest
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


@pytest.mark.xfail(reason="serde_yaml deserializes null as valid string, not caught by validation")
def test_why_null_treated_as_empty(tmp_path):
    """Explicit YAML null in why field should be treated as missing justification."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))

    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: null"))

    result = run_shamefile(str(tmp_path))

    assert result.returncode == 1
