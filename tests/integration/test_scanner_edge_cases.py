import sys

import pytest
import yaml
from conftest import run_shamefile

SIGNAL_EXIT_CODE = 128


def test_binary_file_does_not_crash(tmp_path):
    """Shamefile should not crash when encountering a binary file with null bytes."""
    (tmp_path / "binary.py").write_bytes(b"\x00\x01\x02# noqa\x00\x03")
    (tmp_path / "text.py").write_text("x = 1  # noqa\n")

    result = run_shamefile(tmp_path)

    assert result.returncode < SIGNAL_EXIT_CODE, "process killed by signal"
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    assert any("text.py" in e["location"] for e in registry["entries"])


def test_symlink_to_file_not_followed(tmp_path):
    """Symlinks are not followed — only the real file is scanned, no crash."""
    (tmp_path / "real.py").write_text("x = 1  # noqa\n")
    (tmp_path / "link.py").symlink_to(tmp_path / "real.py")

    result = run_shamefile(tmp_path)

    assert result.returncode < SIGNAL_EXIT_CODE, "process killed by signal"
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    locations = [e["location"] for e in registry["entries"]]

    assert len(registry["entries"]) == 1
    assert any("real.py" in loc for loc in locations)
    assert not any("link.py" in loc for loc in locations)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX chmod(0o000) has no effect on Windows; needs ACL-based equivalent",
)
def test_permission_denied_file_skipped_with_warning(tmp_path):
    """Unreadable files are skipped gracefully with a warning on stderr."""
    ok = tmp_path / "ok.py"
    ok.write_text("x = 1  # noqa\n")
    secret = tmp_path / "secret.py"
    secret.write_text("y = 2  # type: ignore\n")
    secret.chmod(0o000)

    try:
        result = run_shamefile(tmp_path)

        assert result.returncode < SIGNAL_EXIT_CODE, "process killed by signal"
        assert "warning" in result.stderr.lower() or "skipping" in result.stderr.lower()
        assert "Skipped unreadable file" in result.stdout
        assert "secret.py" in result.stdout

        registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
        locations = [e["location"] for e in registry["entries"]]

        assert any("ok.py" in loc for loc in locations)
        assert not any("secret.py" in loc for loc in locations)
    finally:
        secret.chmod(0o644)


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX chmod(0o000) has no effect on Windows; needs ACL-based equivalent",
)
def test_dry_run_reports_skipped_files(tmp_path):
    """Dry-run mode should also surface unreadable files in stdout."""
    (tmp_path / "ok.py").write_text("x = 1  # noqa\n")
    secret = tmp_path / "secret.py"
    secret.write_text("y = 2  # type: ignore\n")

    # Create registry first (normal run), then chmod and re-run with --dry-run.
    run_shamefile(tmp_path)
    secret.chmod(0o000)
    try:
        result = run_shamefile(tmp_path, "--dry-run")

        assert result.returncode < SIGNAL_EXIT_CODE, "process killed by signal"
        assert "Skipped unreadable file" in result.stdout
        assert "secret.py" in result.stdout
    finally:
        secret.chmod(0o644)


def test_unreadable_file_does_not_remove_existing_entries(tmp_path):
    """An unreadable file should not cause its existing registry entries to be removed."""
    target = tmp_path / "target.py"
    target.write_text("x = 1  # noqa\n")

    # First run: create registry with entry
    result = run_shamefile(tmp_path)
    assert result.returncode == 1
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    registry["entries"][0]["why"] = "justified"
    (tmp_path / "shamefile.yaml").write_text(yaml.dump(registry))

    # Make file unreadable
    target.chmod(0o000)
    try:
        # Second run: file is unreadable but entry should survive
        result = run_shamefile(tmp_path)
        registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
        assert any("target.py" in e["location"] for e in registry["entries"]), (
            "Entry for unreadable file was removed"
        )
    finally:
        target.chmod(0o644)
