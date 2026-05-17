"""BDD tests for shame next snippet rendering.

Feature file: features/shame_next_path_traversal.feature.
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

from conftest import BINARY_PATH, run_shame_next
from pytest_bdd import given, parsers, scenarios, then, when

if TYPE_CHECKING:
    from pathlib import Path

scenarios("features/shame_next_path_traversal.feature")


def _entry_yaml(location: str, token: str, content: str) -> str:
    """Format a single registry entry block."""
    return (
        f"  - location: {location}\n"
        f"    token: '{token}'\n"
        f"    content: '{content}'\n"
        "    created_at: 2024-01-01\n"
        "    owner: attacker\n"
        "    why: ''\n"
    )


def _write_registry(project_path: Path, *entries: str) -> None:
    """Write shamefile.yaml containing the given entry blocks in order."""
    yaml = "# yamllint disable-file\n---\nconfig: {}\nentries:\n\n" + "\n".join(entries)
    (project_path / "shamefile.yaml").write_text(yaml, encoding="utf-8")


# --- Given ---


@given("a project with a hand-crafted shamefile.yaml", target_fixture="project")
def project_with_handcrafted_registry(tmp_path):
    """Allocate an empty project directory; registry is filled by later steps."""
    return {"path": tmp_path, "result": None, "secret_path": None}


@given(parsers.parse('a sensitive file outside the project containing "{marker}"'))
def sensitive_file_outside_project(project, tmp_path_factory, marker):
    """Place a file in a sibling tmp directory, outside the project root."""
    outside_dir = tmp_path_factory.mktemp("outside")
    secret_path = outside_dir / "secret.txt"
    secret_path.write_text(f"{marker}\nline two\n", encoding="utf-8")
    project["secret_path"] = secret_path


@given("the registry has an entry whose location is the absolute path of that file at line 1")
def registry_with_absolute_location(project):
    """Write an entry whose location is the absolute path of the sensitive file."""
    abs_path = str(project["secret_path"])
    _write_registry(project["path"], _entry_yaml(f"{abs_path}:1", "# noqa", "placeholder"))


@given('the registry has an entry whose location is a "../"-prefixed path to that file at line 1')
def registry_with_relative_traversal(project):
    """Write an entry whose location is a ../-prefixed path to the sensitive file."""
    rel = os.path.relpath(project["secret_path"], project["path"]).replace("\\", "/")
    _write_registry(project["path"], _entry_yaml(f"{rel}:1", "# noqa", "placeholder"))


@given(
    "the registry has two undocumented entries: "
    "a benign one followed by an absolute path to that file at line 1"
)
def registry_with_benign_then_malicious(project):
    """Write two entries: first benign (to be documented), second malicious (next in queue)."""
    benign = _entry_yaml("./benign.py:1", "# noqa", "benign_content")
    malicious = _entry_yaml(f"{project['secret_path']}:1", "# noqa", "placeholder")
    _write_registry(project["path"], benign, malicious)


@given(
    parsers.parse(
        'the registry has an entry at "{location}" with token "{token}" and content "{content}"'
    )
)
def registry_with_legitimate_entry(project, location, token, content):
    """Write a normal entry at the given relative location."""
    _write_registry(project["path"], _entry_yaml(location, token, content))


# --- When ---


@when("I run shame next")
def run_next(project):
    """Invoke shame next against the project."""
    project["result"] = run_shame_next(project["path"])


@when(parsers.parse('I run shame next with reason "{reason}"'))
def run_next_with_reason(project, reason):
    """Invoke shame next with a reason argument."""
    project["result"] = subprocess.run(
        [BINARY_PATH, "next", reason],
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


@then(parsers.parse('stdout does not contain "{text}"'))
def check_stdout_absent(project, text):
    """Verify stdout does not contain the given substring."""
    assert text not in project["result"].stdout, (
        f"unexpected leak: {text!r} found in stdout:\n{project['result'].stdout}"
    )
