import subprocess

import yaml
from conftest import BINARY_PATH, run_shamefile


def test_rerun_produces_same_yaml(tmp_path):
    """Running shame me twice without changes should produce identical YAML."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry_path = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)
    first_content = registry_path.read_text()

    run_shamefile(tmp_path)
    second_content = registry_path.read_text()

    assert first_content == second_content


def test_shamefile_yaml_not_scanned(tmp_path):
    """Tokens inside shamefile.yaml (e.g. in why field) should not be detected as suppressions."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(tmp_path)

    # Fill why with text containing a suppression token
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'suppressed with # noqa because legacy'"))

    result = run_shamefile(tmp_path)

    # Should still have only 1 entry — shamefile.yaml itself is not scanned
    entries = yaml.safe_load(registry.read_text())["entries"]
    assert len(entries) == 1
    assert result.returncode == 0


def test_shamefile_yaml_not_scanned_with_absolute_path(tmp_path):
    """shamefile.yaml should be excluded from scan even when using absolute path."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")

    # First run to create registry
    run_shamefile(tmp_path)

    # Fill why with a suppression token
    registry_path = tmp_path / "shamefile.yaml"
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'has # noqa in text'"))

    # Rerun with absolute path — different path form than what created the registry
    subprocess.run(
        [BINARY_PATH, "me", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    entries = yaml.safe_load(registry_path.read_text())["entries"]
    for entry in entries:
        assert "shamefile.yaml" not in entry["location"]
