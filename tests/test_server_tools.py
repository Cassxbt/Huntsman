"""Tests for the local file I/O server functions (profile, tracker, story bank)."""

import pytest
from pathlib import Path
from huntsman_mcp.server import _profile_load, _tracker_write, _story_bank_write


# ---------------------------------------------------------------------------
# _tracker_write
# ---------------------------------------------------------------------------

class TestTrackerWrite:
    def test_creates_file_with_header(self, tmp_path):
        _tracker_write(tmp_path, "Stripe", "Senior Engineer", 4.2, "Evaluated")
        content = (tmp_path / "data" / "applications.md").read_text()
        assert "| # | Company | Role |" in content
        assert "Stripe" in content

    def test_first_entry_is_row_1(self, tmp_path):
        _tracker_write(tmp_path, "Stripe", "Senior Engineer", 4.2, "Evaluated")
        content = (tmp_path / "data" / "applications.md").read_text()
        assert "| 1 | Stripe |" in content

    def test_second_entry_is_row_2(self, tmp_path):
        _tracker_write(tmp_path, "Stripe", "Senior Engineer", 4.2, "Evaluated")
        _tracker_write(tmp_path, "Coinbase", "Protocol Engineer", 3.8, "Evaluated")
        content = (tmp_path / "data" / "applications.md").read_text()
        assert "| 2 | Coinbase |" in content

    def test_dedup_updates_existing_row(self, tmp_path):
        _tracker_write(tmp_path, "Stripe", "Senior Engineer", 4.2, "Evaluated")
        result = _tracker_write(tmp_path, "Stripe", "Senior Engineer", 4.2, "Applied")
        assert result["action"] == "updated"
        content = (tmp_path / "data" / "applications.md").read_text()
        assert "Applied" in content

    def test_report_with_pipe_tables_does_not_corrupt_entry_count(self, tmp_path):
        # Block B produces a markdown table with | on every line. If we count
        # those rows on the next call, entry_num will be inflated.
        report = (
            "| JD Requirement | CV Evidence | Match |\n"
            "|---|---|---|\n"
            "| Python 5yr | cv.md line 23 | MATCH |\n"
            "| Kubernetes | No evidence | GAP |\n"
        )
        _tracker_write(tmp_path, "Stripe", "Senior Engineer", 4.2, "Evaluated",
                       report_markdown=report)
        _tracker_write(tmp_path, "Coinbase", "Protocol Engineer", 3.8, "Evaluated")
        content = (tmp_path / "data" / "applications.md").read_text()
        assert "| 2 | Coinbase |" in content

    def test_invalid_status_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Invalid status"):
            _tracker_write(tmp_path, "Stripe", "Engineer", 4.0, "Pending")

    def test_score_formatted_to_one_decimal(self, tmp_path):
        _tracker_write(tmp_path, "Stripe", "Engineer", 4.0, "Evaluated")
        content = (tmp_path / "data" / "applications.md").read_text()
        assert "4.0" in content

    def test_report_appended_below_table(self, tmp_path):
        _tracker_write(tmp_path, "Stripe", "Engineer", 4.0, "Evaluated",
                       report_markdown="## Analysis\nGood fit.")
        content = (tmp_path / "data" / "applications.md").read_text()
        assert "Good fit." in content

    def test_creates_data_dir_if_missing(self, tmp_path):
        assert not (tmp_path / "data").exists()
        _tracker_write(tmp_path, "Stripe", "Engineer", 4.0, "Evaluated")
        assert (tmp_path / "data" / "applications.md").exists()


# ---------------------------------------------------------------------------
# _story_bank_write
# ---------------------------------------------------------------------------

class TestStoryBankWrite:
    def test_creates_file_on_first_write(self, tmp_path):
        _story_bank_write(tmp_path, "## Story 1\nSituation: ...")
        assert (tmp_path / "data" / "story-bank.md").exists()

    def test_content_is_written(self, tmp_path):
        _story_bank_write(tmp_path, "## Story 1\nI led a team of 3.")
        content = (tmp_path / "data" / "story-bank.md").read_text()
        assert "I led a team of 3." in content

    def test_second_write_appends_with_separator(self, tmp_path):
        _story_bank_write(tmp_path, "## Story 1\nContent A")
        _story_bank_write(tmp_path, "## Story 2\nContent B")
        content = (tmp_path / "data" / "story-bank.md").read_text()
        assert "Content A" in content
        assert "Content B" in content
        assert "---" in content

    def test_creates_data_dir_if_missing(self, tmp_path):
        assert not (tmp_path / "data").exists()
        _story_bank_write(tmp_path, "## Story")
        assert (tmp_path / "data" / "story-bank.md").exists()


# ---------------------------------------------------------------------------
# _profile_load
# ---------------------------------------------------------------------------

class TestProfileLoad:
    def test_missing_both_files(self, tmp_path):
        result = _profile_load(tmp_path)
        assert result["profile_yml"] is None
        assert result["cv_md"] is None
        assert "config/profile.yml" in result["missing"]
        assert "cv.md" in result["missing"]

    def test_reads_profile_yml(self, tmp_path):
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "profile.yml").write_text("name: Cass\n")
        result = _profile_load(tmp_path)
        assert "name: Cass" in result["profile_yml"]
        assert "config/profile.yml" not in result["missing"]

    def test_reads_cv_md(self, tmp_path):
        (tmp_path / "cv.md").write_text("# Cass\nSenior Engineer\n")
        result = _profile_load(tmp_path)
        assert "Senior Engineer" in result["cv_md"]
        assert "cv.md" not in result["missing"]

    def test_both_present_no_missing(self, tmp_path):
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "profile.yml").write_text("name: Cass\n")
        (tmp_path / "cv.md").write_text("Experience...\n")
        result = _profile_load(tmp_path)
        assert result["missing"] == []
