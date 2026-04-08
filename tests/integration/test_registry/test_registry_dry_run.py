from conftest import run_shamefile


def test_dry_run_no_registry_exits(tmp_path):
    """Dry-run without existing shamefile.yaml should fail immediately."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    result = run_shamefile("--dry-run", str(tmp_path))

    assert result.returncode == 1
    assert "Registry not found" in result.stderr
    assert "shame me" in result.stderr


def test_dry_run_clean_state_exits(tmp_path):
    """Dry-run on fully justified registry should pass."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", "why: 'Legacy code'"))

    result = run_shamefile("--dry-run", str(tmp_path))

    assert result.returncode == 0
    assert "All checks passed!" in result.stdout


def test_dry_run_undocumented_suppression_exits(tmp_path):
    """Dry-run should fail when code has suppressions not in registry."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    # Create empty registry manually
    registry.write_text("config: {}\nentries: []\n")

    result = run_shamefile("--dry-run", str(tmp_path))

    assert result.returncode == 1
    assert "undocumented" in result.stdout.lower()


def test_dry_run_stale_entry_exits(tmp_path):
    """Dry-run should fail when registry has entries not in code."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile(str(tmp_path))

    # Remove suppression from code
    test_file.write_text("x = 1\n")

    result = run_shamefile("--dry-run", str(tmp_path))

    assert result.returncode == 1
    assert "stale" in result.stdout.lower()


def test_dry_run_missing_why_exits_1(tmp_path):
    """Dry-run should fail when entries have empty why."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile(str(tmp_path))

    result = run_shamefile("--dry-run", str(tmp_path))

    assert result.returncode == 1
    assert "without reason" in result.stdout.lower()


def test_dry_run_does_not_modify_registry(tmp_path):
    """Dry-run should never modify shamefile.yaml."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile(str(tmp_path))
    content_before = registry.read_text()

    # Add new suppression — dry-run should NOT update registry
    test_file.write_text("x = 1  # noqa\ny = 2  # type: ignore\n")

    run_shamefile("--dry-run", str(tmp_path))

    assert registry.read_text() == content_before


def test_dry_run_does_not_create_registry(tmp_path):
    """Dry-run should never create shamefile.yaml."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    registry = tmp_path / "shamefile.yaml"

    run_shamefile("--dry-run", str(tmp_path))

    assert not registry.exists()


def test_dry_run_short_flag_n(tmp_path):
    """Short flag -n should behave the same as --dry-run."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    result_long = run_shamefile("--dry-run", str(tmp_path))
    result_short = run_shamefile("-n", str(tmp_path))

    assert result_long.returncode == result_short.returncode


def test_dry_run_multiple_failures(tmp_path):
    """Dry-run should report all failure types in a single run."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")

    run_shamefile(str(tmp_path))

    # Add new suppression (undocumented) and remove old one (stale)
    test_file.write_text("y = 2  # type: ignore\n")

    result = run_shamefile("--dry-run", str(tmp_path))

    assert result.returncode == 1
    # All three failure types should be reported:
    # - undocumented (# type: ignore not in registry)
    # - stale (# noqa no longer in code)
    # - missing why (original # noqa entry has empty why)
    assert "undocumented" in result.stdout.lower()
    assert "stale" in result.stdout.lower()
    assert "without reason" in result.stdout.lower()
