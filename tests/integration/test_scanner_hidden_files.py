import yaml
from conftest import run_shamefile


def test_hidden_flag_includes_dotfiles(tmp_path):
    """With --hidden, dotfiles like .eslintrc.js should be scanned."""
    (tmp_path / ".eslintrc.js").write_text("// eslint-disable-next-line no-var\nvar x = 1;\n")
    (tmp_path / "visible.py").write_text("y = 2  # type: ignore\n")

    result = run_shamefile(tmp_path, "--hidden")

    assert result.returncode != 2, f"--hidden flag not recognized: {result.stderr}"

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry["entries"]
    locations = [e["location"] for e in entries]

    assert len(entries) == 2
    assert any(".eslintrc.js" in loc for loc in locations)
    assert any("visible.py" in loc for loc in locations)


def test_dotfiles_skipped_by_default(tmp_path):
    """Without --hidden, dotfiles should not be scanned."""
    (tmp_path / ".eslintrc.js").write_text("// eslint-disable-next-line no-var\nvar x = 1;\n")
    (tmp_path / "visible.py").write_text("y = 2  # type: ignore\n")

    result = run_shamefile(tmp_path)

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry["entries"]
    locations = [e["location"] for e in entries]

    assert len(entries) == 1
    assert not any(".eslintrc.js" in loc for loc in locations)
    assert any("visible.py" in loc for loc in locations)


def test_hidden_flag_includes_hidden_directories(tmp_path):
    """With --hidden, files inside hidden directories should be scanned."""
    hidden_dir = tmp_path / ".config"
    hidden_dir.mkdir()
    (hidden_dir / "rules.js").write_text("// eslint-disable-next-line no-var\nvar x = 1;\n")
    (tmp_path / "visible.py").write_text("y = 2  # type: ignore\n")

    result = run_shamefile(tmp_path, "--hidden")

    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry["entries"]
    locations = [e["location"] for e in entries]

    assert len(entries) == 2
    assert any(".config/rules.js" in loc for loc in locations)
    assert any("visible.py" in loc for loc in locations)


def test_hidden_flag_with_dry_run(tmp_path):
    """--hidden combined with --dry-run should scan dotfiles in read-only mode."""
    (tmp_path / ".eslintrc.js").write_text("// eslint-disable-next-line no-var\nvar x = 1;\n")
    (tmp_path / "visible.py").write_text("y = 2  # type: ignore\n")

    # First run: create registry with --hidden
    run_shamefile(tmp_path, "--hidden")
    # Fill in why fields so dry-run passes
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    for entry in registry["entries"]:
        entry["why"] = "test reason"
    (tmp_path / "shamefile.yaml").write_text(yaml.dump(registry, default_flow_style=False))

    # Dry run with --hidden should pass
    result = run_shamefile(tmp_path, "--hidden", "-n")

    assert result.returncode == 0, f"dry-run failed: {result.stdout}"
