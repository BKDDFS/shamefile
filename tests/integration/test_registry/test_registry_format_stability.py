from conftest import run_shamefile


def test_rerun_produces_same_yaml(tmp_path):
    """Running shame me twice without changes should produce identical YAML."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry_path = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))
    first_content = registry_path.read_text()

    run_shamefile(str(tmp_path))
    second_content = registry_path.read_text()

    assert first_content == second_content
