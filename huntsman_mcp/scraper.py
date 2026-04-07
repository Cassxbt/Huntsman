"""LinkedIn page scraper using the navigate-scroll-innerText pattern.

Design principles:
- Extract innerText, not DOM structure. LinkedIn's class names change frequently;
  the visible text hierarchy is far more stable.
- Strip page chrome (footer, sidebar, upsells) before returning content.
- Return raw text per section. Let the LLM parse it — that's what it's good at.
- Be conservative with request timing. A ban during an active job search is painful.
"""

import asyncio
import logging
import random
import re
from typing import Any
from urllib.parse import urlencode, urlparse

from patchright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from huntsman_mcp.browser import get_context
from huntsman_mcp.config import (
    CLICK_DELAY,
    CLICK_JITTER,
    DATE_POSTED_MAP,
    EXPERIENCE_LEVEL_MAP,
    HIGH_VOLUME_EXTRA_DELAY,
    HIGH_VOLUME_THRESHOLD,
    JOB_TYPE_MAP,
    LI_BASE,
    MAX_NAV_RETRIES,
    MAX_SECTION_CHARS,
    NAV_DELAY,
    NAV_JITTER,
    PAGE_TIMEOUT_MS,
    RATE_LIMIT_BACKOFF,
    SCROLL_DELAY,
    SCROLL_JITTER,
    SORT_BY_MAP,
    WORK_TYPE_MAP,
)
from huntsman_mcp.exceptions import (
    AuthRequired,
    NavigationError,
    PrivateProfile,
    ProfileNotFound,
    RateLimited,
    ScrapingError,
    SessionExpired,
)

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")

# Session-level page load counter. Incremented by _navigate().
# Used to trigger extra cooling pauses after sustained volume.
_page_load_count: int = 0


def _validate_slug(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ScrapingError(f"{label} cannot be empty.")
    if not _SLUG_RE.match(value):
        raise ScrapingError(
            f"Invalid {label} {value!r}. "
            "Expected a LinkedIn URL slug containing only letters, numbers, dots, hyphens, and underscores."
        )
    return value


def reset_page_load_count() -> None:
    global _page_load_count
    _page_load_count = 0


def _jitter(base: float, jitter: float) -> float:
    """Return base + a random fraction of jitter. Never negative."""
    return base + random.uniform(0, jitter)


async def _jitter_sleep(base: float, jitter: float) -> None:
    """Sleep for base + random jitter seconds."""
    await asyncio.sleep(_jitter(base, jitter))


PERSON_SECTIONS = frozenset(
    ["experience", "education", "skills", "honors", "languages", "contact_info", "posts"]
)

# LinkedIn footer/sidebar chrome that bleeds into innerText.
_NOISE_MARKERS: list[re.Pattern[str]] = [
    re.compile(r"^About\n+(?:Accessibility|Talent Solutions)", re.MULTILINE),
    re.compile(r"^More profiles for you$", re.MULTILINE),
    re.compile(r"^Explore premium profiles$", re.MULTILINE),
    re.compile(r"^Get up to .+ replies when you message with InMail$", re.MULTILINE),
    re.compile(
        r"^(?:Careers|Privacy & Terms|Questions\?|Select language)\n+"
        r"(?:Privacy & Terms|Questions\?|Select language|Advertising|Ad Choices)",
        re.MULTILINE,
    ),
]

_NOISE_LINES: list[re.Pattern[str]] = [
    re.compile(r"^(?:Play|Pause|Playback speed|Turn fullscreen on|Fullscreen)$"),
    re.compile(r"^(?:Show captions|Close modal window|Media player modal window)$"),
    re.compile(r"^(?:Loaded:.*|Remaining time.*|Stream Type.*)$"),
]


# Internal helpers

def _strip_noise(text: str) -> str:
    """Remove LinkedIn page chrome from raw innerText."""
    # Truncate at the first known footer/sidebar marker.
    earliest = len(text)
    for pattern in _NOISE_MARKERS:
        match = pattern.search(text)
        if match and match.start() < earliest:
            earliest = match.start()
    text = text[:earliest].strip()

    # Filter known media/control noise lines.
    lines = [
        line
        for line in text.splitlines()
        if not any(p.match(line.strip()) for p in _NOISE_LINES)
    ]
    return "\n".join(lines).strip()


def _lookup(value: str, mapping: dict[str, str], filter_name: str) -> str:
    """Look up a single value in a mapping. Raises ScrapingError on unknown."""
    if value not in mapping:
        valid = ", ".join(sorted(mapping.keys()))
        raise ScrapingError(
            f"Invalid {filter_name} {value!r}. Valid values: {valid}."
        )
    return mapping[value]


def _normalize_csv_filter(value: str, mapping: dict[str, str], filter_name: str) -> str:
    """Map a comma-separated list of human-readable filter names to LinkedIn
    URL parameter values. Raises ScrapingError if any value is unknown.
    """
    parts = [v.strip() for v in value.split(",") if v.strip()]
    unknown = [p for p in parts if p not in mapping]
    if unknown:
        valid = ", ".join(sorted(mapping.keys()))
        raise ScrapingError(
            f"Invalid {filter_name} value(s): {', '.join(unknown)}. "
            f"Valid values: {valid}."
        )
    return ",".join(mapping[p] for p in parts)


def _path_matches_prefix(path: str, prefix: str) -> bool:
    """Return True if `path` is exactly `prefix` or a subpath of it.

    Comparison is case-insensitive (LinkedIn lowercases usernames in
    redirects). Trailing slashes on either side do not affect the match.
    """
    p = path.rstrip("/").lower()
    pre = prefix.rstrip("/").lower()
    return p == pre or p.startswith(pre + "/")


async def _navigate(page: Page, url: str) -> None:
    """Navigate to a URL with jitter, retry on timeout, and backoff on rate limits.

    Strategy:
    - Every navigation sleeps for NAV_DELAY + random jitter (avoids fixed-interval
      bot fingerprint that LinkedIn's detection looks for)
    - After HIGH_VOLUME_THRESHOLD page loads, inserts an extra cooling pause
    - On rate-limit detection (429 / redirect), waits with exponential backoff
      before retrying (15s → 30s → 60s)
    - After MAX_NAV_RETRIES failures raises NavigationError
    """
    global _page_load_count

    for attempt in range(MAX_NAV_RETRIES):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
            _page_load_count += 1

            # Post-navigation jitter sleep.
            await _jitter_sleep(NAV_DELAY, NAV_JITTER)

            # If this session is high-volume, add a cooling pause.
            if _page_load_count > 0 and _page_load_count % HIGH_VOLUME_THRESHOLD == 0:
                cooling = HIGH_VOLUME_EXTRA_DELAY + random.uniform(0, 3.0)
                logger.info(
                    "High-volume pause after %d page loads (%.1fs)", _page_load_count, cooling
                )
                await asyncio.sleep(cooling)

            # Check for rate limit immediately after navigation resolves.
            current_url = page.url
            if (
                "too-many-requests" in current_url
                or "429" in current_url
                or "request_challenge" in current_url
            ):
                backoff = RATE_LIMIT_BACKOFF * (2 ** attempt)
                logger.warning(
                    "Rate limited on %s (attempt %d/%d). Waiting %.0fs before retry...",
                    url, attempt + 1, MAX_NAV_RETRIES, backoff,
                )
                await asyncio.sleep(backoff + random.uniform(0, 5.0))
                continue  # Retry the navigation.

            return

        except PlaywrightTimeoutError:
            if attempt < MAX_NAV_RETRIES - 1:
                wait = (NAV_DELAY * 2) + random.uniform(0, 3.0)
                logger.warning(
                    "Navigation timeout for %s (attempt %d/%d). Retrying in %.1fs...",
                    url, attempt + 1, MAX_NAV_RETRIES, wait,
                )
                await asyncio.sleep(wait)
            else:
                raise NavigationError(
                    f"Page {url!r} did not load after {MAX_NAV_RETRIES} attempts. "
                    "Check your internet connection and try again."
                )

    raise NavigationError(
        f"Page {url!r} was rate-limited on all {MAX_NAV_RETRIES} attempts. "
        "Wait a few minutes before retrying."
    )


def _check_page_state(
    page: Page,
    identifier: str,
    *,
    expected_path_prefix: str | None = None,
) -> None:
    """Raise the appropriate error based on the page's current URL.

    Must be called synchronously right after _navigate() completes.

    If `expected_path_prefix` is provided, the final URL path must match it
    (or be a subpath). This positive check catches unknown LinkedIn redirects
    that would otherwise return garbage data to the agent.
    """
    url = page.url

    if "authwall" in url or "checkpoint" in url or "login" in url:
        raise SessionExpired(
            "Your LinkedIn session has expired. "
            "Run `huntsman-mcp --login` to re-authenticate."
        )

    if "429" in url or "too-many-requests" in url or "request_challenge" in url:
        raise RateLimited(
            "LinkedIn is rate limiting requests. Wait a few minutes, then retry."
        )

    parsed = urlparse(url)

    # LinkedIn returns a redirect to /404 or /unavailable for missing pages.
    if parsed.path.rstrip("/") in ("/404", "/unavailable", "/error"):
        raise ProfileNotFound(
            f"No LinkedIn page found for {identifier!r}. "
            "Verify the username or URL is correct."
        )

    # Positive path validation — final URL must be on the expected section.
    # Catches unknown redirects (e.g., to a country-restriction page) that
    # would otherwise pass through and return garbage data.
    if expected_path_prefix and not _path_matches_prefix(parsed.path, expected_path_prefix):
        raise NavigationError(
            f"Unexpected redirect for {identifier!r}: ended on {parsed.path!r} "
            f"instead of a path under {expected_path_prefix!r}. "
            "LinkedIn may have changed its routing."
        )


async def _scroll_to_bottom(page: Page) -> None:
    """Scroll incrementally with jitter to trigger lazy-loaded section rendering.

    Incremental scrolling mimics human reading behaviour and forces LinkedIn's
    IntersectionObserver to render sections that are lazy-loaded off-screen.
    Jitter on each step avoids the robotic fixed-interval scroll signature.
    """
    scroll_height: int = await page.evaluate("document.body.scrollHeight")
    viewport_height: int = await page.evaluate("window.innerHeight")
    position = 0

    while position < scroll_height:
        # Vary the scroll step slightly — humans don't scroll in exact viewport increments.
        step = int(viewport_height * random.uniform(0.7, 1.1))
        position = min(position + step, scroll_height)
        await page.evaluate(f"window.scrollTo(0, {position})")
        await _jitter_sleep(SCROLL_DELAY, SCROLL_JITTER)

    # Scroll back to top so subsequent interactions start from a known position.
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(0.3 + random.uniform(0, 0.3))


async def _expand_truncated_content(page: Page) -> None:
    """Click all visible 'see more' and 'show all' buttons to expand truncated text.

    LinkedIn truncates long About sections, experience descriptions, etc.
    We expand everything before extracting innerText.
    """
    # These aria-label patterns are more stable than class names.
    selector = (
        "button[aria-label*='see more'], "
        "button[aria-label*='Show all'], "
        "button[aria-label*='show more'], "
        "button.inline-show-more-text__button, "
        "span[role='button'][aria-label*='more']"
    )
    buttons = await page.query_selector_all(selector)
    for btn in buttons:
        try:
            if await btn.is_visible():
                await btn.click()
                await _jitter_sleep(CLICK_DELAY, CLICK_JITTER)
        except Exception:
            # A click failure on one button should not abort the whole extraction.
            pass


async def _page_inner_text(page: Page, selector: str = "main") -> str | None:
    """Return stripped innerText of the first element matching selector, or None.

    The result is truncated to MAX_SECTION_CHARS so a multi-tool pipeline
    cannot exhaust the agent's context window on a single oversized scrape.
    """
    el = await page.query_selector(selector)
    if el is None:
        return None
    raw = await el.inner_text()
    cleaned = _strip_noise(raw)
    if not cleaned:
        return None
    if len(cleaned) > MAX_SECTION_CHARS:
        cleaned = cleaned[:MAX_SECTION_CHARS] + "\n\n[...content truncated]"
    return cleaned


async def _open_contact_info_modal(page: Page) -> str | None:
    """Click the 'Contact info' link, wait for the modal, extract its text."""
    try:
        contact_link = await page.query_selector(
            "a[href*='contact-info'], "
            "a[id*='contact-info'], "
            "section#contact-info a"
        )
        if contact_link is None:
            return None
        await contact_link.click()
        await asyncio.sleep(CLICK_DELAY * 1.5)

        modal = await page.query_selector("div[role='dialog'], div.pv-profile-section__section-info")
        if modal is None:
            return None

        text = await modal.inner_text()
        cleaned = _strip_noise(text)

        # Close modal before continuing.
        close_btn = await page.query_selector(
            "button[aria-label='Dismiss'], button[aria-label='Close']"
        )
        if close_btn:
            await close_btn.click()
            await asyncio.sleep(0.5)

        return cleaned or None
    except Exception as exc:
        logger.debug("contact_info extraction failed: %s", exc)
        return None


# Public scraper methods

async def scrape_person(
    username: str,
    sections: set[str] | None = None,
) -> dict[str, Any]:
    """Scrape a LinkedIn person profile.

    Args:
        username: LinkedIn username (e.g. 'williamhgates').
        sections: Set of section names to fetch in addition to the main profile page.
                  Valid values: experience, education, skills, honors, languages,
                  contact_info, posts. Pass None to fetch main page only.

    Returns:
        Dict with keys:
            url: Canonical profile URL.
            sections: Mapping of section name → raw stripped innerText.
            unknown_sections: List of section names that were not recognised.
    """
    username = _validate_slug(username, "username")
    ctx = await get_context()
    page = await ctx.new_page()
    result: dict[str, Any] = {
        "url": f"{LI_BASE}/in/{username}/",
        "sections": {},
        "unknown_sections": [],
    }

    try:
        profile_url = f"{LI_BASE}/in/{username}/"
        await _navigate(page, profile_url)
        _check_page_state(page, username, expected_path_prefix=f"/in/{username}")

        await _scroll_to_bottom(page)
        await _expand_truncated_content(page)

        main_text = await _page_inner_text(page, "main")
        if not main_text:
            raise ScrapingError(
                f"Profile page for {username!r} loaded but no content was extracted. "
                "The profile may be private or LinkedIn has changed its layout."
            )
        result["sections"]["main"] = main_text

        if not sections:
            return result

        # Validate section names up front.
        unknown = [s for s in sections if s not in PERSON_SECTIONS]
        if unknown:
            result["unknown_sections"] = unknown
        valid_sections = sections & PERSON_SECTIONS

        if "contact_info" in valid_sections:
            contact_text = await _open_contact_info_modal(page)
            if contact_text:
                result["sections"]["contact_info"] = contact_text

        # LinkedIn serves these at /details/{section}/.
        subpage_map = {
            "experience": f"{LI_BASE}/in/{username}/details/experience/",
            "education": f"{LI_BASE}/in/{username}/details/education/",
            "skills": f"{LI_BASE}/in/{username}/details/skills/",
            "honors": f"{LI_BASE}/in/{username}/details/honors/",
            "languages": f"{LI_BASE}/in/{username}/details/languages/",
        }

        for section, url in subpage_map.items():
            if section not in valid_sections:
                continue
            try:
                await _navigate(page, url)
                _check_page_state(
                    page,
                    f"{username}/{section}",
                    expected_path_prefix=f"/in/{username}",
                )

                if page.url.rstrip("/") == profile_url.rstrip("/"):
                    logger.debug("Section %r is empty for %s", section, username)
                    continue

                await _scroll_to_bottom(page)
                await _expand_truncated_content(page)
                text = await _page_inner_text(page, "main")
                if text:
                    result["sections"][section] = text
            except (ProfileNotFound, PrivateProfile):
                logger.debug("Section %r unavailable for %s", section, username)
            except (RateLimited, SessionExpired):
                raise
            except Exception as exc:
                logger.warning("Failed to scrape section %r for %s: %s", section, username, exc)

        if "posts" in valid_sections:
            try:
                posts_url = f"{LI_BASE}/in/{username}/recent-activity/all/"
                await _navigate(page, posts_url)
                _check_page_state(
                    page,
                    f"{username}/posts",
                    expected_path_prefix=f"/in/{username}",
                )
                await _scroll_to_bottom(page)
                text = await _page_inner_text(page, "main")
                if text:
                    result["sections"]["posts"] = text
            except Exception as exc:
                logger.warning("Failed to scrape posts for %s: %s", username, exc)

    finally:
        await page.close()

    return result


async def scrape_company(identifier: str) -> dict[str, Any]:
    """Scrape a LinkedIn company page.

    Args:
        identifier: Company slug from the LinkedIn URL (e.g. 'google', 'stripe').
                    Also accepts a full linkedin.com/company/... URL.

    Returns:
        Dict with url and sections keys.
    """
    # Normalise: strip any URL prefix to get just the slug.
    if "/" in identifier:
        identifier = identifier.rstrip("/").split("/")[-1]
    identifier = _validate_slug(identifier, "company_identifier")

    ctx = await get_context()
    page = await ctx.new_page()
    result: dict[str, Any] = {
        "url": f"{LI_BASE}/company/{identifier}/",
        "sections": {},
    }

    try:
        await _navigate(page, result["url"])
        _check_page_state(
            page,
            identifier,
            expected_path_prefix=f"/company/{identifier}",
        )
        await _scroll_to_bottom(page)
        await _expand_truncated_content(page)

        main_text = await _page_inner_text(page, "main")
        if not main_text:
            raise ScrapingError(
                f"Company page for {identifier!r} loaded but no content was extracted."
            )
        result["sections"]["main"] = main_text

        about_url = f"{LI_BASE}/company/{identifier}/about/"
        try:
            await _navigate(page, about_url)
            _check_page_state(
                page,
                f"{identifier}/about",
                expected_path_prefix=f"/company/{identifier}",
            )
            await _scroll_to_bottom(page)
            text = await _page_inner_text(page, "main")
            if text:
                result["sections"]["about"] = text
        except Exception as exc:
            logger.debug("Company about page failed for %s: %s", identifier, exc)

    finally:
        await page.close()

    return result


async def scrape_job(job_id: str) -> dict[str, Any]:
    """Scrape a LinkedIn job posting by job ID.

    Args:
        job_id: Numeric LinkedIn job ID (e.g. '4252026496').

    Returns:
        Dict with url and sections keys.
    """
    if job_id.startswith("http"):
        parsed = urlparse(job_id)
        if parsed.hostname not in ("www.linkedin.com", "linkedin.com"):
            raise ScrapingError(
                f"Invalid job URL {job_id!r}. Only linkedin.com/jobs/view/... URLs are accepted."
            )
        if not parsed.path.startswith("/jobs/view/"):
            raise ScrapingError(
                f"URL {job_id!r} is not a LinkedIn job posting. "
                "Path must start with /jobs/view/."
            )
        match = re.search(r"/view/(\d+)", parsed.path)
        job_id = match.group(1) if match else parsed.path.rstrip("/").split("/")[-1]
        url = f"{LI_BASE}/jobs/view/{job_id}/"
    else:
        if not job_id.isdigit():
            raise ScrapingError(
                f"Invalid job ID {job_id!r}. Expected a numeric ID like '4252026496'."
            )
        url = f"{LI_BASE}/jobs/view/{job_id}/"

    ctx = await get_context()
    page = await ctx.new_page()
    result: dict[str, Any] = {"url": url, "sections": {}}

    try:
        await _navigate(page, url)
        _check_page_state(page, job_id, expected_path_prefix="/jobs/view")

        await _expand_truncated_content(page)
        await _scroll_to_bottom(page)

        text = await _page_inner_text(page, "main")
        if not text:
            raise ScrapingError(f"Job posting {job_id!r} loaded but no content was extracted.")
        result["sections"]["main"] = text

    finally:
        await page.close()

    return result


async def search_jobs(
    keywords: str,
    *,
    location: str | None = None,
    max_pages: int = 3,
    date_posted: str | None = None,
    job_type: str | None = None,
    experience_level: str | None = None,
    work_type: str | None = None,
    easy_apply: bool = False,
    sort_by: str | None = None,
) -> dict[str, Any]:
    """Search LinkedIn jobs and return raw text with a list of extracted job IDs.

    Args:
        keywords: Search query (e.g. 'senior solidity engineer').
        location: Location filter (e.g. 'Remote', 'New York').
        max_pages: Number of result pages to load (1–10).
        date_posted: 'past_hour', 'past_24_hours', 'past_week', or 'past_month'.
        job_type: Comma-separated: full_time, part_time, contract, temporary, internship, other.
        experience_level: Comma-separated: internship, entry, associate, mid_senior, director, executive.
        work_type: Comma-separated: on_site, remote, hybrid.
        easy_apply: Only show Easy Apply jobs.
        sort_by: 'date' or 'relevance'.

    Returns:
        Dict with url, sections (page text), and job_ids (list of numeric ID strings
        suitable for passing to scrape_job()).
    """
    max_pages = max(1, min(10, max_pages))

    params: dict[str, str] = {"keywords": keywords}
    if location:
        params["location"] = location
    if date_posted:
        params["f_TPR"] = _lookup(date_posted, DATE_POSTED_MAP, "date_posted")
    if job_type:
        params["f_JT"] = _normalize_csv_filter(job_type, JOB_TYPE_MAP, "job_type")
    if experience_level:
        params["f_E"] = _normalize_csv_filter(
            experience_level, EXPERIENCE_LEVEL_MAP, "experience_level"
        )
    if work_type:
        params["f_WT"] = _normalize_csv_filter(work_type, WORK_TYPE_MAP, "work_type")
    if easy_apply:
        params["f_AL"] = "true"
    if sort_by:
        params["sortBy"] = _lookup(sort_by, SORT_BY_MAP, "sort_by")

    base_search_url = f"{LI_BASE}/jobs/search/?" + urlencode(params)

    ctx = await get_context()
    page = await ctx.new_page()
    result: dict[str, Any] = {
        "url": base_search_url,
        "sections": {},
        "job_ids": [],
    }

    try:
        all_text_parts: list[str] = []
        all_job_ids: list[str] = []

        for page_num in range(max_pages):
            paginated_params = {**params, "start": str(page_num * 25)}
            page_url = f"{LI_BASE}/jobs/search/?" + urlencode(paginated_params)

            await _navigate(page, page_url)
            _check_page_state(
                page, keywords, expected_path_prefix="/jobs/search"
            )
            await _scroll_to_bottom(page)

            text = await _page_inner_text(page, "main")
            if text:
                all_text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

            # Extract job IDs from data attributes in the rendered HTML.
            job_ids_on_page: list[str] = await page.evaluate("""
                () => {
                    const ids = new Set();
                    document.querySelectorAll('[data-job-id], [data-occludable-job-id]').forEach(el => {
                        const id = el.getAttribute('data-job-id') || el.getAttribute('data-occludable-job-id');
                        if (id && /^\\d+$/.test(id)) ids.add(id);
                    });
                    // Also pull from job card links as fallback.
                    document.querySelectorAll('a[href*="/jobs/view/"]').forEach(a => {
                        const m = a.href.match(/\\/jobs\\/view\\/(\\d+)/);
                        if (m) ids.add(m[1]);
                    });
                    return Array.from(ids);
                }
            """)
            all_job_ids.extend(job_ids_on_page)

            # If we got fewer than ~10 IDs, we've hit the last page of results.
            if len(job_ids_on_page) < 10 and page_num > 0:
                break

        if all_text_parts:
            result["sections"]["search_results"] = "\n\n".join(all_text_parts)

        # Deduplicate while preserving order.
        seen: set[str] = set()
        for jid in all_job_ids:
            if jid not in seen:
                seen.add(jid)
                result["job_ids"].append(jid)

    finally:
        await page.close()

    return result


async def search_people(
    keywords: str,
    *,
    location: str | None = None,
) -> dict[str, Any]:
    """Search for people on LinkedIn.

    Useful for finding recruiters at target companies or hiring managers.

    Args:
        keywords: Search query (e.g. 'blockchain recruiter', 'engineering manager stripe').
        location: Optional location string. Best-effort: appended to the keywords
            query so LinkedIn matches it against profile text. The structured
            geoUrn filter requires a numeric LinkedIn geo URN (e.g.
            'urn:li:geo:90000049') which is not derivable from plain names.

    Returns:
        Dict with url and sections keys. The LLM should parse the raw text
        to extract individual profiles from the search results.
    """
    effective_keywords = f"{keywords} {location}".strip() if location else keywords
    params: dict[str, str] = {
        "keywords": effective_keywords,
        "origin": "SWITCH_SEARCH_VERTICAL",
    }

    url = f"{LI_BASE}/search/results/people/?" + urlencode(params)

    ctx = await get_context()
    page = await ctx.new_page()
    result: dict[str, Any] = {"url": url, "sections": {}}

    try:
        await _navigate(page, url)
        _check_page_state(
            page, keywords, expected_path_prefix="/search/results/people"
        )
        await _scroll_to_bottom(page)

        text = await _page_inner_text(page, "main")
        if text:
            result["sections"]["search_results"] = text

    finally:
        await page.close()

    return result
