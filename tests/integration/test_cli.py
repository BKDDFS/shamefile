import subprocess

import yaml
from conftest import BINARY_PATH

CLAP_USAGE_EXIT_CODE = 2


def test_dot_path_scans_current_directory(tmp_path):
    """'shame me .' should scan the current directory."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")

    result = subprocess.run(
        [BINARY_PATH, "me", "."],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 1
    assert (tmp_path / "shamefile.yaml").exists()


def test_shamefile_created_at_git_root(tmp_path):
    """Running from git repo subdir should create shamefile.yaml at git root."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    src = tmp_path / "src"
    src.mkdir()
    (src / "test.py").write_text("x = 1  # noqa\n")

    subprocess.run([BINARY_PATH, "me", "."], capture_output=True, text=True, cwd=src, check=False)

    assert (tmp_path / "shamefile.yaml").exists()
    assert not (src / "shamefile.yaml").exists()


def test_shamefile_created_in_cwd_without_git(tmp_path):
    """Without a git repo, shamefile.yaml should be created in CWD."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "test.py").write_text("x = 1  # noqa\n")

    subprocess.run(
        [BINARY_PATH, "me", "src"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert (tmp_path / "shamefile.yaml").exists()
    assert not (src / "shamefile.yaml").exists()


def test_scan_path_scopes_what_is_scanned(tmp_path):
    """'shame me src' should only scan src/, not sibling directories."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "test.py").write_text("x = 1  # noqa\n")

    other = tmp_path / "other"
    other.mkdir()
    (other / "test.py").write_text("y = 2  # type: ignore\n")

    subprocess.run(
        [BINARY_PATH, "me", "src"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    # shamefile.yaml should be in CWD with entries only from src/
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry["entries"]
    assert len(entries) == 1
    assert "# noqa" in entries[0]["token"]


def test_single_file_path_scans_that_file(tmp_path):
    """'shame me src/app.py' should scan that single file."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("x = 1  # noqa\n")
    (src / "utils.py").write_text("y = 2  # type: ignore\n")

    result = subprocess.run(
        [BINARY_PATH, "me", "src/app.py"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 1
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry["entries"]
    assert len(entries) == 1
    assert "# noqa" in entries[0]["token"]


def test_single_file_with_git_uses_git_root(tmp_path):
    """'shame me app.py' from subdir of git repo should place registry at git root."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("x = 1  # noqa\n")

    subprocess.run(
        [BINARY_PATH, "me", "app.py"],
        capture_output=True,
        text=True,
        cwd=src,
        check=False,
    )

    assert (tmp_path / "shamefile.yaml").exists()
    assert not (src / "shamefile.yaml").exists()


def test_single_file_without_git_uses_cwd(tmp_path):
    """Without git, registry should be placed at CWD, not file's directory."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("x = 1  # noqa\n")

    subprocess.run(
        [BINARY_PATH, "me", "src/app.py"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert (tmp_path / "shamefile.yaml").exists()
    assert not (src / "shamefile.yaml").exists()


def test_no_path_defaults_to_current_directory(tmp_path):
    """'shame me' without path should default to scanning current directory."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")

    result = subprocess.run(
        [BINARY_PATH, "me"], capture_output=True, text=True, cwd=tmp_path, check=False
    )

    assert result.returncode == 1
    assert (tmp_path / "shamefile.yaml").exists()


def test_no_subcommand_shows_usage():
    """Running bare 'shame' without subcommand should show usage."""
    result = subprocess.run([BINARY_PATH], capture_output=True, text=True, check=False)

    assert result.returncode == CLAP_USAGE_EXIT_CODE
    combined = result.stdout + result.stderr
    assert "Usage: shame <COMMAND>" in combined
    assert "me" in combined


def test_multiple_paths_scans_all(tmp_path):
    """'shame me src tests' should scan both directories."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("x = 1  # noqa\n")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_foo.py").write_text("y = 2  # type: ignore\n")

    result = subprocess.run(
        [BINARY_PATH, "me", "src", "tests"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 1
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    entries = registry["entries"]
    tokens = {e["token"] for e in entries}
    assert "# noqa" in tokens
    assert "# type: ignore" in tokens


def test_multiple_paths_fail_fast_on_missing(tmp_path):
    """If any path doesn't exist, fail before scanning."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text("x = 1  # noqa\n")

    result = subprocess.run(
        [BINARY_PATH, "me", "src", "nonexistent"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 1
    assert "nonexistent" in result.stderr
    assert not (tmp_path / "shamefile.yaml").exists()


def test_multiple_paths_deduplicates_overlapping(tmp_path):
    """Overlapping paths should not produce duplicate entries."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")

    result = subprocess.run(
        [BINARY_PATH, "me", ".", "."],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 1
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    assert len(registry["entries"]) == 1


def test_absolute_vs_relative_path_produces_same_location(tmp_path):
    """Same file scanned via '.' and absolute path should produce identical location."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    registry_path = tmp_path / "shamefile.yaml"

    # Run 1: relative path
    subprocess.run(
        [BINARY_PATH, "me", "."],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    loc_relative = yaml.safe_load(registry_path.read_text())["entries"][0]["location"]
    registry_path.unlink()

    # Run 2: absolute path
    subprocess.run(
        [BINARY_PATH, "me", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    loc_absolute = yaml.safe_load(registry_path.read_text())["entries"][0]["location"]

    assert loc_relative == loc_absolute


def test_rerun_with_different_path_form_preserves_justified_entries(tmp_path):
    """Justified entry should survive rerun with absolute path after initial relative run."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    registry_path = tmp_path / "shamefile.yaml"

    # Run 1: relative path
    subprocess.run(
        [BINARY_PATH, "me", "."],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    # Fill why
    content = registry_path.read_text()
    registry_path.write_text(content.replace("why: ''", "why: 'Justified reason'"))

    # Run 2: absolute path — same location, different form
    result = subprocess.run(
        [BINARY_PATH, "me", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )

    entries = yaml.safe_load(registry_path.read_text())["entries"]
    assert len(entries) == 1
    assert entries[0]["why"] == "Justified reason"
    assert "Removing stale entry" not in result.stdout
    assert "New suppression detected" not in result.stdout
    assert result.returncode == 0


def test_dot_dot_with_git_normalizes_location(tmp_path):
    """'shame me ..' from git subdirectory should normalize location without '..'."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    subdir = tmp_path / "sub"
    subdir.mkdir()

    result = subprocess.run(
        [BINARY_PATH, "me", ".."],
        capture_output=True,
        text=True,
        cwd=subdir,
        check=False,
    )

    assert result.returncode == 1
    registry_path = tmp_path / "shamefile.yaml"
    assert registry_path.exists()
    entries = yaml.safe_load(registry_path.read_text())["entries"]
    assert ".." not in entries[0]["location"]


def test_dot_dot_without_git_rejected(tmp_path):
    """'shame me ..' without git should reject path outside project root."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    subdir = tmp_path / "sub"
    subdir.mkdir()

    result = subprocess.run(
        [BINARY_PATH, "me", ".."],
        capture_output=True,
        text=True,
        cwd=subdir,
        check=False,
    )

    assert result.returncode == 1
    assert "outside" in result.stderr.lower()
    assert not (subdir / "shamefile.yaml").exists()
