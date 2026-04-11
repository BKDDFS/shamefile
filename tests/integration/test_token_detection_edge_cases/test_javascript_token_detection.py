import pytest
from conftest import XFAIL_STRING_DETECTION, run_shamefile


@pytest.mark.xfail(reason=XFAIL_STRING_DETECTION)
def test_token_inside_template_literal_is_not_detected(tmp_path):
    """Token inside a JS template literal is not a real suppression."""
    test_file = tmp_path / "test.js"
    test_file.write_text("const msg = `add // eslint-disable above the line`;\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    assert "// eslint-disable" not in result.stdout


def test_block_level_suppression(tmp_path):
    """Block-level suppression like /* eslint-disable */ should be detected."""
    test_file = tmp_path / "test.js"
    test_file.write_text("/* eslint-disable */\nconst x = 1;\n/* eslint-enable */\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "eslint-disable" in result.stdout


def test_next_line_variant_detected(tmp_path):
    """'// eslint-disable-next-line' contains '// eslint-disable' and should be detected."""
    test_file = tmp_path / "test.js"
    test_file.write_text("// eslint-disable-next-line no-var\nvar x = 1;\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "// eslint-disable" in result.stdout
