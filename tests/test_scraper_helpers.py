"""Golden tests for scraper helper functions."""

import pytest
from huntsman_mcp.scraper import (
    _lookup,
    _normalize_csv_filter,
    _path_matches_prefix,
    _strip_noise,
)
from huntsman_mcp.config import (
    DATE_POSTED_MAP,
    JOB_TYPE_MAP,
    EXPERIENCE_LEVEL_MAP,
    WORK_TYPE_MAP,
    SORT_BY_MAP,
)
from huntsman_mcp.exceptions import ScrapingError


# ---------------------------------------------------------------------------
# _path_matches_prefix
# ---------------------------------------------------------------------------

class TestPathMatchesPrefix:
    def test_exact_match(self):
        assert _path_matches_prefix("/in/cassxbt", "/in/cassxbt")

    def test_trailing_slash_on_path(self):
        assert _path_matches_prefix("/in/cassxbt/", "/in/cassxbt")

    def test_trailing_slash_on_prefix(self):
        assert _path_matches_prefix("/in/cassxbt", "/in/cassxbt/")

    def test_subpath_matches(self):
        assert _path_matches_prefix("/in/cassxbt/details/experience/", "/in/cassxbt")

    def test_case_insensitive(self):
        # LinkedIn lowercases usernames in redirects.
        assert _path_matches_prefix("/in/CASSXBT", "/in/cassxbt")
        assert _path_matches_prefix("/in/cassxbt", "/in/CASSXBT")

    def test_different_user_no_match(self):
        assert not _path_matches_prefix("/in/someone_else", "/in/cassxbt")

    def test_partial_username_no_match(self):
        # /in/cassxbt-extra should NOT match /in/cassxbt
        assert not _path_matches_prefix("/in/cassxbt-extra", "/in/cassxbt")

    def test_company_path(self):
        assert _path_matches_prefix("/company/stripe/about/", "/company/stripe")

    def test_jobs_view(self):
        assert _path_matches_prefix("/jobs/view/1234567890/", "/jobs/view")

    def test_wrong_section_no_match(self):
        assert not _path_matches_prefix("/jobs/search", "/in/cassxbt")

    def test_search_people(self):
        assert _path_matches_prefix(
            "/search/results/people/?keywords=recruiter",
            "/search/results/people",
        )


# ---------------------------------------------------------------------------
# _lookup
# ---------------------------------------------------------------------------

class TestLookup:
    def test_valid_date_posted(self):
        assert _lookup("past_week", DATE_POSTED_MAP, "date_posted") == "r604800"
        assert _lookup("past_hour", DATE_POSTED_MAP, "date_posted") == "r3600"
        assert _lookup("past_24_hours", DATE_POSTED_MAP, "date_posted") == "r86400"
        assert _lookup("past_month", DATE_POSTED_MAP, "date_posted") == "r2592000"

    def test_valid_sort_by(self):
        assert _lookup("date", SORT_BY_MAP, "sort_by") == "DD"
        assert _lookup("relevance", SORT_BY_MAP, "sort_by") == "R"

    def test_unknown_value_raises(self):
        with pytest.raises(ScrapingError, match="Invalid date_posted"):
            _lookup("yesterday", DATE_POSTED_MAP, "date_posted")

    def test_error_message_lists_valid_values(self):
        with pytest.raises(ScrapingError, match="past_hour"):
            _lookup("bad_value", DATE_POSTED_MAP, "date_posted")


# ---------------------------------------------------------------------------
# _normalize_csv_filter
# ---------------------------------------------------------------------------

class TestNormalizeCsvFilter:
    def test_single_valid_job_type(self):
        assert _normalize_csv_filter("full_time", JOB_TYPE_MAP, "job_type") == "F"

    def test_multiple_valid_job_types(self):
        result = _normalize_csv_filter("full_time,contract", JOB_TYPE_MAP, "job_type")
        assert result == "F,C"

    def test_whitespace_trimmed(self):
        result = _normalize_csv_filter("full_time , contract", JOB_TYPE_MAP, "job_type")
        assert result == "F,C"

    def test_experience_level_mapping(self):
        assert _normalize_csv_filter("mid_senior", EXPERIENCE_LEVEL_MAP, "experience_level") == "4"
        assert _normalize_csv_filter("entry,associate", EXPERIENCE_LEVEL_MAP, "experience_level") == "2,3"

    def test_work_type_mapping(self):
        assert _normalize_csv_filter("remote", WORK_TYPE_MAP, "work_type") == "2"
        assert _normalize_csv_filter("on_site,hybrid", WORK_TYPE_MAP, "work_type") == "1,3"

    def test_unknown_value_raises(self):
        with pytest.raises(ScrapingError, match="job_type"):
            _normalize_csv_filter("gig", JOB_TYPE_MAP, "job_type")

    def test_mixed_valid_invalid_raises(self):
        with pytest.raises(ScrapingError, match="gig"):
            _normalize_csv_filter("full_time,gig", JOB_TYPE_MAP, "job_type")

    def test_all_job_types_map(self):
        for key in JOB_TYPE_MAP:
            result = _normalize_csv_filter(key, JOB_TYPE_MAP, "job_type")
            assert result == JOB_TYPE_MAP[key]


# ---------------------------------------------------------------------------
# _strip_noise
# ---------------------------------------------------------------------------

class TestStripNoise:
    def test_plain_content_preserved(self):
        text = "Senior Engineer at Stripe\nBuilt payment systems"
        result = _strip_noise(text)
        assert "Senior Engineer" in result
        assert "Built payment systems" in result

    def test_handles_empty_input(self):
        assert _strip_noise("") == ""

    def test_strips_leading_trailing_whitespace(self):
        result = _strip_noise("\n\nSome content\n\n")
        assert result == "Some content"

    def test_truncates_at_footer_marker(self):
        # "About\nAccessibility" is a known LinkedIn footer pattern.
        text = "Profile content\nAbout\nAccessibility\nMore noise"
        result = _strip_noise(text)
        assert "Profile content" in result
        assert "Accessibility" not in result

    def test_removes_media_control_lines(self):
        # "Play" and "Pause" are known LinkedIn video control noise.
        text = "Work experience\nPlay\nPause\nArchitected systems"
        result = _strip_noise(text)
        assert "Work experience" in result
        assert "Architected systems" in result
        assert "Play" not in result
        assert "Pause" not in result
