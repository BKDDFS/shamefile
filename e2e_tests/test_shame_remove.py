"""BDD tests for shame remove — feature file: features/shame_remove.feature."""

import subprocess

import yaml
from conftest import BINARY_PATH, run_shame_fix, run_shame_remove, run_shamefile
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/shame_remove.feature")

FIVE_SUPPRESSIONS = (
    "a = 1  # noqa\nb = 2  # type: ignore\nc = 3  # nosec\n"
    "d = 4  # pragma: no cover\ne = 5  # fmt: off\n"
)


# --- Given ---


@given("a project with five suppressions", target_fixture="project")
def project_with_five_suppressions(tmp_path):
    """Create a project with five different suppressions and run initial shame me."""
    (tmp_path / "test.py").write_text(FIVE_SUPPRESSIONS, encoding="utf-8")
    run_shamefile(tmp_path)
    return {"path": tmp_path, "result": None, "registry_snapshot": None}


@given("a project with one undocumented suppression", target_fixture="project")
def project_with_one_suppression(tmp_path):
    """Create a project with a single # noqa suppression."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n", encoding="utf-8")
    run_shamefile(tmp_path)
    return {"path": tmp_path, "result": None, "registry_snapshot": None}


@given("a project with no registry", target_fixture="project")
def project_with_no_registry(tmp_path):
    """Create an empty project where shamefile.yaml does not exist."""
    return {"path": tmp_path, "result": None, "registry_snapshot": None}


@given(parsers.parse('the entry "{location}" "{token}" has why "{why}"'))
def set_entry_why(project, location, token, why):
    """Document a specific entry by running shame fix."""
    run_shame_fix(project["path"], location, token, "--why", why)


@given("the registry contents are captured")
def capture_registry(project):
    """Snapshot the registry file before invoking the command under test."""
    project["registry_snapshot"] = (project["path"] / "shamefile.yaml").read_text(encoding="utf-8")


# --- When ---


@when(parsers.parse('I run shame remove "{location}" "{token}"'))
def run_remove(project, location, token):
    """Invoke `shame remove` for the given (location, token) pair."""
    project["result"] = run_shame_remove(project["path"], location, token)


@when(parsers.parse('I run shame rm "{location}" "{token}"'))
def run_rm(project, location, token):
    """Invoke the `rm` alias of `shame remove`."""
    project["result"] = subprocess.run(
        [BINARY_PATH, "rm", location, token],
        capture_output=True,
        text=True,
        cwd=str(project["path"]),
        check=False,
    )


@when(parsers.parse('I run shame remove "{location}" without the token argument'))
def run_remove_missing_token(project, location):
    """Invoke `shame remove` without the required positional token to trigger a clap error."""
    project["result"] = subprocess.run(
        [BINARY_PATH, "remove", location],
        capture_output=True,
        text=True,
        cwd=str(project["path"]),
        check=False,
    )


# --- Then ---


@then(parsers.parse("the command exits with code {code:d}"))
def check_exit_code(project, code):
    """Verify the last command's exit code."""
    assert project["result"].returncode == code, (
        f"exit code {project['result'].returncode}\n"
        f"stdout: {project['result'].stdout}\n"
        f"stderr: {project['result'].stderr}"
    )


@then(parsers.parse('stdout contains "{text}"'))
def check_stdout_contains(project, text):
    """Verify stdout contains the given substring."""
    assert text in project["result"].stdout, f"{text!r} not in stdout: {project['result'].stdout!r}"


@then(parsers.parse('stderr contains "{text}"'))
def check_stderr_contains(project, text):
    """Verify stderr contains the given substring."""
    assert text in project["result"].stderr, f"{text!r} not in stderr: {project['result'].stderr!r}"


@then(parsers.parse("shamefile.yaml has {count:d} entries"))
def check_entry_count(project, count):
    """Verify the registry contains the expected number of entries."""
    entries = yaml.safe_load((project["path"] / "shamefile.yaml").read_text())["entries"]
    assert len(entries) == count, f"expected {count} entries, got {len(entries)}"


@then(parsers.parse('shamefile.yaml contains token "{token}"'))
def check_token_present(project, token):
    """Verify the registry contains an entry with the given token."""
    entries = yaml.safe_load((project["path"] / "shamefile.yaml").read_text())["entries"]
    tokens = [e["token"] for e in entries]
    assert token in tokens, f"token {token!r} not in {tokens!r}"


@then(parsers.parse('shamefile.yaml does not contain token "{token}"'))
def check_token_absent(project, token):
    """Verify the registry has no entry with the given token."""
    entries = yaml.safe_load((project["path"] / "shamefile.yaml").read_text())["entries"]
    tokens = [e["token"] for e in entries]
    assert token not in tokens, f"unexpected token {token!r} still in {tokens!r}"


@then(parsers.parse('the entry "{location}" "{token}" has why "{why}"'))
def check_entry_why(project, location, token, why):
    """Verify the why field of the entry identified by (location, token)."""
    entries = yaml.safe_load((project["path"] / "shamefile.yaml").read_text())["entries"]
    entry = next((e for e in entries if e["location"] == location and e["token"] == token), None)
    assert entry is not None, f"no entry at {location} with token {token!r}"
    assert entry["why"] == why, f"entry why = {entry['why']!r}, expected {why!r}"


@then("the registry contents are unchanged")
def check_registry_unchanged(project):
    """Verify the registry file is byte-for-byte identical to the captured snapshot."""
    snapshot = project["registry_snapshot"]
    assert snapshot is not None, "registry snapshot was not captured"
    current = (project["path"] / "shamefile.yaml").read_text(encoding="utf-8")
    assert current == snapshot, "registry file was modified despite no-match"
