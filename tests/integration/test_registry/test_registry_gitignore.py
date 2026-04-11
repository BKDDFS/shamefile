import subprocess

import yaml
from conftest import run_shamefile


def test_nested_gitignore_respected(tmp_path):
    """A .gitignore in a subdirectory should only affect that subdirectory."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)

    # Root file — should always be scanned
    (tmp_path / "root.py").write_text("x = 1  # noqa\n")

    # src/ has its own .gitignore ignoring *.generated.py
    src = tmp_path / "src"
    src.mkdir()
    (src / ".gitignore").write_text("*.generated.py\n")
    (src / "kept.py").write_text("y = 2  # type: ignore\n")
    (src / "skip.generated.py").write_text("z = 3  # nosec\n")

    # Root-level generated file — NOT ignored (nested .gitignore doesn't apply here)
    (tmp_path / "root.generated.py").write_text("w = 4  # noqa\n")

    run_shamefile(tmp_path)

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    locations = [e["location"] for e in registry["entries"]]

    assert any("root.py" in loc for loc in locations)
    assert any("kept.py" in loc for loc in locations)
    assert any("root.generated.py" in loc for loc in locations)
    assert not any("skip.generated.py" in loc for loc in locations)


def test_gitignore_negation_pattern(tmp_path):
    """Negation pattern (!) should re-include a previously ignored file."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)

    (tmp_path / ".gitignore").write_text("*.log.py\n!important.log.py\n")
    (tmp_path / "debug.log.py").write_text("x = 1  # noqa\n")
    (tmp_path / "important.log.py").write_text("y = 2  # type: ignore\n")

    run_shamefile(tmp_path)

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    locations = [e["location"] for e in registry["entries"]]

    assert not any("debug.log.py" in loc for loc in locations)
    assert any("important.log.py" in loc for loc in locations)
