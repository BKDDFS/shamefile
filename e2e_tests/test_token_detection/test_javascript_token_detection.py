import yaml
from conftest import run_shamefile


def test_token_inside_template_literal_is_not_detected(tmp_path):
    """Token inside a JS template literal is not a real suppression."""
    test_file = tmp_path / "test.js"
    test_file.write_text("const msg = `add // eslint-disable above the line`;\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry.get("entries") or []
    assert not any("eslint-disable" in e["token"] for e in entries)


def test_token_inside_string_is_not_detected(tmp_path):
    """Token inside a JS string literal is not a real suppression."""
    test_file = tmp_path / "test.js"
    test_file.write_text('const msg = "add // eslint-disable above the line";\n')

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry.get("entries") or []
    assert not any("eslint-disable" in e["token"] for e in entries)


def test_block_level_suppression(tmp_path):
    """Block-level suppression like /* eslint-disable */ should be detected."""
    test_file = tmp_path / "test.js"
    test_file.write_text("/* eslint-disable */\nconst x = 1;\n/* eslint-enable */\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    assert any("eslint-disable" in e["token"] for e in registry["entries"])


def test_next_line_variant_detected(tmp_path):
    """'// eslint-disable-next-line' contains '// eslint-disable' and should be detected."""
    test_file = tmp_path / "test.js"
    test_file.write_text("// eslint-disable-next-line no-var\nvar x = 1;\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    assert any("// eslint-disable" in e["token"] for e in registry["entries"])
