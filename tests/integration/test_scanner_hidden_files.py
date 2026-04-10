import pytest
import yaml

from conftest import run_shamefile


@pytest.mark.xfail(reason="--hidden flag not implemented yet — dotfiles should be scannable via opt-in flag")
def test_hidden_flag_includes_dotfiles(tmp_path):
    """With --hidden, dotfiles like .eslintrc.js should be scanned."""
    (tmp_path / ".eslintrc.js").write_text("// eslint-disable-next-line no-var\nvar x = 1;\n")
    (tmp_path / "visible.py").write_text("y = 2  # type: ignore\n")

    result = run_shamefile("--hidden", str(tmp_path))

    assert result.returncode != 2, f"--hidden flag not recognized: {result.stderr}"

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry["entries"]
    locations = [e["location"] for e in entries]

    assert len(entries) == 2
    assert any(".eslintrc.js" in loc for loc in locations)
    assert any("visible.py" in loc for loc in locations)
