"""Runtime configuration: paths, delays, and LinkedIn URL constants."""

from pathlib import Path

# --- Storage ---
APP_DIR = Path.home() / ".local" / "share" / "huntsman-mcp"
BROWSER_PROFILE_DIR = APP_DIR / "browser_profile"

# Converted documents (PDFs, DOCXs) are written here by default.
# Users can override via the HUNTSMAN_OUTPUT_DIR environment variable.
import os as _os
_output_env = _os.environ.get("HUNTSMAN_OUTPUT_DIR")
OUTPUT_DIR = Path(_output_env) if _output_env else Path.home() / "Downloads"

# --- Timing ---
# All delays have jitter applied at call sites (see scraper._jitter_sleep).
# Fixed intervals are a bot signature — jitter makes the pattern human-like.

# Base delay between page navigations. LinkedIn tracks request cadence.
NAV_DELAY: float = 2.5
# Maximum random seconds added on top of NAV_DELAY per navigation.
NAV_JITTER: float = 1.8

# Between scroll steps while triggering lazy-loaded sections.
SCROLL_DELAY: float = 0.6
SCROLL_JITTER: float = 0.4

# After clicking a "Show more" / "See all" button before re-extracting.
CLICK_DELAY: float = 1.0
CLICK_JITTER: float = 0.5

# Page load timeout in milliseconds.
PAGE_TIMEOUT_MS: int = 30_000
# Max retry attempts when a page times out or returns a rate limit response.
MAX_NAV_RETRIES: int = 3

# Maximum characters per scraped page section returned to the agent.
# Truncates the tail to keep the agent's context window manageable across
# a multi-tool pipeline. 8000 chars ≈ 2000 tokens — covers a typical
# LinkedIn profile / job / company page after noise stripping.
MAX_SECTION_CHARS: int = 8000

# Initial wait (seconds) after detecting a rate limit. Doubles each retry.
# Sequence: 15s → 30s → 60s.
RATE_LIMIT_BACKOFF: float = 15.0

# After this many page loads in a single session, insert longer cooling pauses.
# LinkedIn's detection is cumulative — sustained volume triggers throttling.
HIGH_VOLUME_THRESHOLD: int = 12
HIGH_VOLUME_EXTRA_DELAY: float = 4.0

# --- LinkedIn URL base ---
LI_BASE = "https://www.linkedin.com"

# --- Job search filter maps (LinkedIn URL parameter values) ---
DATE_POSTED_MAP: dict[str, str] = {
    "past_hour": "r3600",
    "past_24_hours": "r86400",
    "past_week": "r604800",
    "past_month": "r2592000",
}

EXPERIENCE_LEVEL_MAP: dict[str, str] = {
    "internship": "1",
    "entry": "2",
    "associate": "3",
    "mid_senior": "4",
    "director": "5",
    "executive": "6",
}

JOB_TYPE_MAP: dict[str, str] = {
    "full_time": "F",
    "part_time": "P",
    "contract": "C",
    "temporary": "T",
    "volunteer": "V",
    "internship": "I",
    "other": "O",
}

WORK_TYPE_MAP: dict[str, str] = {
    "on_site": "1",
    "remote": "2",
    "hybrid": "3",
}

SORT_BY_MAP: dict[str, str] = {
    "date": "DD",
    "relevance": "R",
}
