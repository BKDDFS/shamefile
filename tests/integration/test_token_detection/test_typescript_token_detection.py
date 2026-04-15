import yaml
from conftest import run_shamefile


def test_token_inside_string_is_not_detected(tmp_path):
    """Token inside a TS string literal is not a real suppression."""
    test_file = tmp_path / "test.ts"
    test_file.write_text('const msg: string = "use // @ts-ignore for escape hatch";\n')

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry.get("entries") or []
    assert not any("@ts-ignore" in e["token"] for e in entries)


def test_token_inside_template_literal_is_not_detected(tmp_path):
    """Token inside a TS template literal is not a real suppression."""
    test_file = tmp_path / "test.ts"
    test_file.write_text("const msg: string = `use // @ts-ignore for escape hatch`;\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 0
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry.get("entries") or []
    assert not any("@ts-ignore" in e["token"] for e in entries)


def test_token_alone_on_line(tmp_path):
    """Token on its own line (suppressing the next line) should be detected."""
    test_file = tmp_path / "test.ts"
    test_file.write_text("// @ts-ignore\nconst x: any = unsafeCall();\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    assert any("// @ts-ignore" in e["token"] for e in registry["entries"])


def test_block_comment_tslint_detected(tmp_path):
    """/* tslint:disable */ block comment should be detected."""
    test_file = tmp_path / "test.ts"
    test_file.write_text("/* tslint:disable */\nconst x = 1;\n/* tslint:enable */\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    assert any("tslint:disable" in e["token"] for e in registry["entries"])


def test_jsx_ts_ignore_detected(tmp_path):
    """JSX-style {/* @ts-ignore */} should be detected."""
    test_file = tmp_path / "test.tsx"
    test_file.write_text("{/* @ts-ignore */}\n<Component prop={unsafeValue} />\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    assert any("@ts-ignore" in e["token"] for e in registry["entries"])
