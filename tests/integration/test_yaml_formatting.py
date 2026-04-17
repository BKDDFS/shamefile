"""BDD tests for YAML formatting — feature file: features/yaml_formatting_docstring.feature."""

import subprocess

import yaml
from conftest import BINARY_PATH, run_shamefile
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/yaml_formatting_docstring.feature")


# --- Given ---


@given("a project with one suppression", target_fixture="project")
def project_with_suppression(tmp_path):
    """Create a project with one # noqa suppression and run initial shame me."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    run_shamefile(tmp_path)
    return {"path": tmp_path, "result": None}


@given(
    "a project with one suppression and manual edit:",
    target_fixture="project",
)
def project_with_manual_edit(tmp_path, docstring):
    """Create project, then replace why: '' with the docstring content."""
    (tmp_path / "test.py").write_text("x = 1  # noqa\n")
    run_shamefile(tmp_path)
    registry = tmp_path / "shamefile.yaml"
    content = registry.read_text()
    registry.write_text(content.replace("why: ''", docstring.strip()))
    return {"path": tmp_path, "result": None}


# --- When ---


@when("I run shame next with reason:")
def run_next_with_reason(project, docstring):
    """Run shame next with the docstring as the reason argument."""
    project["result"] = subprocess.run(
        [BINARY_PATH, "next", docstring],
        capture_output=True,
        text=True,
        cwd=str(project["path"]),
        check=False,
    )


@when("I run shame me")
def run_shame_me(project):
    """Run shame me to trigger normalization."""
    project["result"] = run_shamefile(project["path"])


# --- Then ---


def _parse_yaml_lines(docstring: str) -> dict:
    """Parse a YAML-like docstring into a dict of expected key:value pairs."""
    return yaml.safe_load(docstring) or {}


@then("shamefile.yaml contains entry with:")
def check_yaml_contains_entry_with(project, docstring):
    """Verify the first entry in shamefile.yaml contains the expected raw lines."""
    raw = (project["path"] / "shamefile.yaml").read_text()
    for line in docstring.strip().splitlines():
        assert line in raw, f"Expected line {line!r} not found in shamefile.yaml"


@then(parsers.parse("shame me exits with code {code:d}"))
def check_exit_code(project, code):
    """Verify shame me returncode."""
    assert project["result"].returncode == code


@then("no line in shamefile.yaml exceeds 80 characters")
def check_max_line_length(project):
    """Verify yamllint-friendly line length."""
    raw = (project["path"] / "shamefile.yaml").read_text()
    max_line_length = 80
    for line in raw.splitlines():
        assert len(line) <= max_line_length, (
            f"Line exceeds {max_line_length} chars ({len(line)}): {line}"
        )


@then("shamefile.yaml passes yamllint with default config")
def check_yamllint(project):
    """Verify generated YAML passes yamllint defaults."""
    result = subprocess.run(
        ["yamllint", "-d", "default", str(project["path"] / "shamefile.yaml")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"yamllint failed:\n{result.stdout}"
