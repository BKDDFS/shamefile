from datetime import UTC, date, datetime, timedelta

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
    assert single_entry["token"] == "# noqa"  # noqa: S105


def test_entry_has_correct_location(single_entry):
    """Entry location should contain file path and line number."""
    assert single_entry["location"].endswith("test.py:1")


def test_entry_has_empty_why_on_creation(single_entry):
    """New entry should have empty why, waiting for developer to fill in."""
    assert single_entry["why"] == ""


def test_entry_has_recent_created_at(single_entry):
    """Entry created_at should be today's UTC date."""
    created_at = single_entry["created_at"]
    today = datetime.now(UTC).date()

    assert isinstance(created_at, date)
    assert today - created_at <= timedelta(days=1)


def test_entry_has_content(single_entry):
    """Every new entry must have a content field."""
    assert "content" in single_entry
    assert isinstance(single_entry["content"], str)
    assert len(single_entry["content"]) > 0
