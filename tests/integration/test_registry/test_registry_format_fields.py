from datetime import UTC, datetime, timedelta

import pytest
import yaml
from conftest import run_shamefile


@pytest.fixture
def single_entry(tmp_path):
    """Create a file with one suppression, run shamefile, return the entry."""
    test_file = tmp_path / "test.py"
    test_file.write_text("x = 1  # noqa\n")
    run_shamefile(tmp_path)
    registry = yaml.safe_load((tmp_path / "shamefile.yaml").read_text())
    return registry["entries"][0]


def test_entry_has_correct_token(single_entry):
    """Entry token should match the detected suppression."""
    assert single_entry["token"] == "# noqa"


def test_entry_has_correct_location(single_entry):
    """Entry location should contain file path and line number."""
    assert single_entry["location"].endswith("test.py:1")


def test_entry_has_empty_why_on_creation(single_entry):
    """New entry should have empty why, waiting for developer to fill in."""
    assert single_entry["why"] == ""


def test_entry_has_recent_created_at(single_entry):
    """Entry created_at should be a recent UTC timestamp."""
    created_at = single_entry["created_at"]
    now = datetime.now(UTC)

    assert isinstance(created_at, datetime)
    assert now - created_at < timedelta(minutes=5)
