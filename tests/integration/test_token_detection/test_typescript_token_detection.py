from conftest import run_shamefile


def test_token_alone_on_line(tmp_path):
    """Token on its own line (suppressing the next line) should be detected."""
    test_file = tmp_path / "test.ts"
    test_file.write_text("// @ts-ignore\nconst x: any = unsafeCall();\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "// @ts-ignore" in result.stdout


def test_block_comment_tslint_detected(tmp_path):
    """/* tslint:disable */ block comment should be detected."""
    test_file = tmp_path / "test.ts"
    test_file.write_text("/* tslint:disable */\nconst x = 1;\n/* tslint:enable */\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "tslint:disable" in result.stdout


def test_jsx_ts_ignore_detected(tmp_path):
    """JSX-style {/* @ts-ignore */} should be detected."""
    test_file = tmp_path / "test.tsx"
    test_file.write_text("{/* @ts-ignore */}\n<Component prop={unsafeValue} />\n")

    result = run_shamefile(tmp_path)

    assert result.returncode == 1
    assert "@ts-ignore" in result.stdout
