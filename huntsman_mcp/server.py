"""FastMCP server — tool definitions and CLI entry point.

Tools exposed:
    get_linkedin_profile   — person profile with configurable sections
    get_linkedin_company   — company page + about subpage
    get_linkedin_job       — single job posting
    search_linkedin_jobs   — job search with filters
    search_linkedin_people — people/recruiter search
    convert_resume         — Markdown → PDF or DOCX
    load_profile           — read config/profile.yml and cv.md from project root
    write_tracker          — append/update a row in data/applications.md
    write_story_bank       — append STAR+R stories to data/story-bank.md
    search_reddit          — search Reddit posts (salary, interviews, reviews)
    get_reddit_post        — full post + comments
    get_reddit_subreddit   — browse a subreddit (hot/top/new)

CLI modes (not MCP server):
    huntsman-mcp --setup   Install Patchright Chromium browser
    huntsman-mcp --login   Authenticate with LinkedIn
    huntsman-mcp --status  Check session validity
"""

import asyncio
import datetime
import logging
import sys
from typing import Annotated, Any, NoReturn

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from huntsman_mcp import __version__
from huntsman_mcp.auth import ensure_logged_in, print_status, run_login
from huntsman_mcp.config import get_project_dir
from huntsman_mcp.exceptions import (
    AuthRequired,
    BrowserSetupError,
    HuntsmanError,
    NavigationError,
    PrivateProfile,
    ProfileNotFound,
    RateLimited,
    ScrapingError,
    SessionExpired,
)
from huntsman_mcp.converter import ConversionError, to_docx_async, to_pdf
from huntsman_mcp.reddit import (
    get_reddit_post as _get_reddit_post,
    get_subreddit_posts as _get_subreddit_posts,
    search_reddit as _search_reddit,
)
from huntsman_mcp.scraper import (
    PERSON_SECTIONS,
    scrape_company,
    scrape_job,
    scrape_person,
    search_jobs,
    search_people,
)

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "huntsman-mcp",
    version=__version__,
    instructions=(
        "LinkedIn profile auditing, resume tailoring, company research, job search, "
        "and Reddit intelligence. LinkedIn tools require a valid session — "
        "run `huntsman-mcp --login` first. Reddit tools work without auth."
    ),
)


# Error mapping

def _raise_as_tool_error(exc: Exception, tool_name: str) -> NoReturn:
    """Map huntsman exceptions to user-friendly ToolError messages."""
    if isinstance(exc, (AuthRequired, SessionExpired)):
        raise ToolError(str(exc)) from exc
    if isinstance(exc, RateLimited):
        raise ToolError(str(exc)) from exc
    if isinstance(exc, ProfileNotFound):
        raise ToolError(str(exc)) from exc
    if isinstance(exc, PrivateProfile):
        raise ToolError(str(exc)) from exc
    if isinstance(exc, BrowserSetupError):
        raise ToolError(str(exc)) from exc
    if isinstance(exc, (ScrapingError, NavigationError)):
        raise ToolError(f"{tool_name}: {exc}") from exc
    if isinstance(exc, HuntsmanError):
        raise ToolError(f"{tool_name}: {exc}") from exc
    # Unknown exceptions bubble up so FastMCP's error masking can handle them.
    raise exc


# Tools

@mcp.tool(
    title="Get LinkedIn Profile",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_linkedin_profile(
    linkedin_username: str,
    ctx: Context,
    sections: Annotated[
        str | None,
        Field(
            description=(
                "Comma-separated extra sections to fetch beyond the main profile page. "
                "Available: experience, education, skills, honors, languages, contact_info, posts. "
                "Example: 'experience,education,skills'. Default: main page only."
            )
        ),
    ] = None,
) -> dict[str, Any]:
    """Get a LinkedIn person's profile.

    Returns the profile's main page text plus any requested extra sections.
    Each section is raw innerText — the agent should parse and interpret it.

    Args:
        linkedin_username: Username from the LinkedIn profile URL.
                           e.g. 'williamhgates' from linkedin.com/in/williamhgates
        sections: Comma-separated section names (see parameter description).
    """
    await ctx.report_progress(0, 100, "Checking session...")
    try:
        await ensure_logged_in()
    except (AuthRequired, SessionExpired) as exc:
        raise ToolError(str(exc)) from exc

    requested: set[str] | None = None
    unknown: list[str] = []

    if sections:
        parts = {s.strip().lower() for s in sections.split(",") if s.strip()}
        unknown = [s for s in parts if s not in PERSON_SECTIONS]
        requested = parts & PERSON_SECTIONS

    logger.info("get_linkedin_profile: username=%s sections=%s", linkedin_username, sections)
    await ctx.report_progress(10, 100, f"Scraping profile: {linkedin_username}")

    try:
        result = await scrape_person(linkedin_username, sections=requested)
    except Exception as exc:
        _raise_as_tool_error(exc, "get_linkedin_profile")

    if unknown:
        result.setdefault("unknown_sections", []).extend(unknown)

    await ctx.report_progress(100, 100, "Complete")
    return result


@mcp.tool(
    title="Get LinkedIn Company",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_linkedin_company(
    company_identifier: str,
    ctx: Context,
) -> dict[str, Any]:
    """Get a LinkedIn company page.

    Useful for pre-application research: what language does the company use,
    what do they emphasise, what are their recent posts and announcements.

    Args:
        company_identifier: Company slug from the LinkedIn URL
                            (e.g. 'google' from linkedin.com/company/google)
                            or the full linkedin.com/company/... URL.
    """
    await ctx.report_progress(0, 100, "Checking session...")
    try:
        await ensure_logged_in()
    except (AuthRequired, SessionExpired) as exc:
        raise ToolError(str(exc)) from exc

    logger.info("get_linkedin_company: identifier=%s", company_identifier)
    await ctx.report_progress(10, 100, f"Scraping company: {company_identifier}")

    try:
        result = await scrape_company(company_identifier)
    except Exception as exc:
        _raise_as_tool_error(exc, "get_linkedin_company")

    await ctx.report_progress(100, 100, "Complete")
    return result


@mcp.tool(
    title="Get LinkedIn Job Details",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_linkedin_job(
    job_id: str,
    ctx: Context,
) -> dict[str, Any]:
    """Get the full details of a LinkedIn job posting.

    Use this to retrieve the complete job description before tailoring a resume
    or writing a cover letter.

    Args:
        job_id: Numeric LinkedIn job ID (e.g. '4252026496')
                or a full linkedin.com/jobs/view/... URL.
    """
    await ctx.report_progress(0, 100, "Checking session...")
    try:
        await ensure_logged_in()
    except (AuthRequired, SessionExpired) as exc:
        raise ToolError(str(exc)) from exc

    logger.info("get_linkedin_job: job_id=%s", job_id)
    await ctx.report_progress(10, 100, f"Scraping job: {job_id}")

    try:
        result = await scrape_job(job_id)
    except Exception as exc:
        _raise_as_tool_error(exc, "get_linkedin_job")

    await ctx.report_progress(100, 100, "Complete")
    return result


@mcp.tool(
    title="Search LinkedIn Jobs",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def search_linkedin_jobs(
    keywords: str,
    ctx: Context,
    location: str | None = None,
    max_pages: Annotated[int, Field(ge=1, le=10)] = 3,
    date_posted: Annotated[
        str | None,
        Field(description="past_hour | past_24_hours | past_week | past_month"),
    ] = None,
    job_type: Annotated[
        str | None,
        Field(description="Comma-separated: full_time, part_time, contract, temporary, internship, other"),
    ] = None,
    experience_level: Annotated[
        str | None,
        Field(description="Comma-separated: internship, entry, associate, mid_senior, director, executive"),
    ] = None,
    work_type: Annotated[
        str | None,
        Field(description="Comma-separated: on_site, remote, hybrid"),
    ] = None,
    easy_apply: bool = False,
    sort_by: Annotated[
        str | None,
        Field(description="date | relevance"),
    ] = None,
) -> dict[str, Any]:
    """Search LinkedIn for job postings.

    Returns raw search result text plus a list of job_ids that can be passed
    to get_linkedin_job for full posting details.

    Args:
        keywords: Search query (e.g. 'senior solidity engineer', 'fullstack web3').
        location: Location filter. Use 'Remote' for remote roles.
        max_pages: Number of result pages to load (1–10, default 3, ~25 jobs/page).
        date_posted: Filter by posting recency.
        job_type: Filter by employment type.
        experience_level: Filter by seniority level.
        work_type: Filter by work arrangement.
        easy_apply: Set True to show only Easy Apply jobs.
        sort_by: Sort by 'date' or 'relevance'.
    """
    await ctx.report_progress(0, 100, "Checking session...")
    try:
        await ensure_logged_in()
    except (AuthRequired, SessionExpired) as exc:
        raise ToolError(str(exc)) from exc

    logger.info("search_linkedin_jobs: keywords=%r location=%s", keywords, location)
    await ctx.report_progress(10, 100, f"Searching: {keywords}")

    try:
        result = await search_jobs(
            keywords,
            location=location,
            max_pages=max_pages,
            date_posted=date_posted,
            job_type=job_type,
            experience_level=experience_level,
            work_type=work_type,
            easy_apply=easy_apply,
            sort_by=sort_by,
        )
    except Exception as exc:
        _raise_as_tool_error(exc, "search_linkedin_jobs")

    await ctx.report_progress(100, 100, "Complete")
    return result


@mcp.tool(
    title="Search LinkedIn People",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def search_linkedin_people(
    keywords: str,
    ctx: Context,
    location: str | None = None,
) -> dict[str, Any]:
    """Search for people on LinkedIn.

    Use this to find recruiters at target companies, hiring managers,
    or to research competitor developer profiles.

    Args:
        keywords: Search query (e.g. 'blockchain recruiter', 'engineering manager stripe',
                  'senior solidity developer').
        location: Optional location string. Best-effort: appended to the keywords
                  query so LinkedIn full-text matches it against profile content.
                  This is not a structured filter — LinkedIn's geoUrn parameter
                  requires a numeric geo URN that can't be derived from a name.
    """
    await ctx.report_progress(0, 100, "Checking session...")
    try:
        await ensure_logged_in()
    except (AuthRequired, SessionExpired) as exc:
        raise ToolError(str(exc)) from exc

    logger.info("search_linkedin_people: keywords=%r location=%s", keywords, location)
    await ctx.report_progress(10, 100, f"Searching people: {keywords}")

    try:
        result = await search_people(keywords, location=location)
    except Exception as exc:
        _raise_as_tool_error(exc, "search_linkedin_people")

    await ctx.report_progress(100, 100, "Complete")
    return result


@mcp.tool(
    title="Convert Resume",
    annotations={"readOnlyHint": False},
)
async def convert_resume(
    markdown_content: str,
    ctx: Context,
    output_format: Annotated[
        str,
        Field(description="Output format: 'pdf' or 'docx'"),
    ],
    filename: Annotated[
        str,
        Field(
            description=(
                "Output filename without extension (e.g. 'resume_fullstack'). "
                "The file is saved to ~/Downloads/ by default, or the path set in "
                "the HUNTSMAN_OUTPUT_DIR environment variable."
            )
        ),
    ],
) -> dict[str, Any]:
    """Convert a resume from Markdown to PDF or DOCX.

    Use this immediately after generating or tailoring a resume. The output
    file is saved to ~/Downloads/ (or HUNTSMAN_OUTPUT_DIR if set).

    Args:
        markdown_content: Full resume text in Huntsman Markdown format.
        output_format: 'pdf' or 'docx'.
        filename: Base filename without extension (e.g. 'resume_fullstack').

    Returns:
        Dict with output_path (absolute path to the generated file) and
        file_size_bytes.
    """
    fmt = output_format.lower().strip()
    if fmt not in ("pdf", "docx"):
        raise ToolError(
            f"Invalid output_format {output_format!r}. Use 'pdf' or 'docx'."
        )

    if not markdown_content.strip():
        raise ToolError("markdown_content is empty. Provide the full resume text.")

    logger.info("convert_resume: format=%s filename=%s", fmt, filename)
    await ctx.report_progress(0, 100, f"Converting to {fmt.upper()}...")

    try:
        if fmt == "pdf":
            output_path = await to_pdf(markdown_content, filename)
        else:
            output_path = await to_docx_async(markdown_content, filename)
    except ConversionError as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"convert_resume: unexpected error: {exc}") from exc

    await ctx.report_progress(100, 100, "Complete")

    return {
        "output_path": str(output_path),
        "file_size_bytes": output_path.stat().st_size,
        "format": fmt,
    }


@mcp.tool(
    title="Load Profile",
    annotations={"readOnlyHint": True},
)
async def load_profile(ctx: Context) -> dict[str, Any]:
    """Load the user's profile and CV from the project directory.

    Returns the raw contents of config/profile.yml and cv.md.
    Call this at the start of every session instead of reading files directly —
    the tool resolves paths reliably regardless of the agent's working directory.

    Returns:
        Dict with profile_yml (str or None), cv_md (str or None), and
        missing (list of filenames that do not exist yet — triggers onboarding).
    """
    project = get_project_dir()
    profile_path = project / "config" / "profile.yml"
    cv_path = project / "cv.md"

    result: dict[str, Any] = {"profile_yml": None, "cv_md": None, "missing": []}

    if profile_path.exists():
        result["profile_yml"] = profile_path.read_text(encoding="utf-8")
    else:
        result["missing"].append("config/profile.yml")

    if cv_path.exists():
        result["cv_md"] = cv_path.read_text(encoding="utf-8")
    else:
        result["missing"].append("cv.md")

    return result


_TRACKER_HEADER = (
    "| # | Company | Role | Score | Status | Date | Notes |\n"
    "|---|---------|------|-------|--------|------|-------|\n"
)

_VALID_TRACKER_STATUSES = frozenset(
    ["Evaluated", "CV Sent", "Applied", "Interview", "Offer", "Rejected", "Skipped", "Withdrawn"]
)


@mcp.tool(
    title="Write Tracker",
    annotations={"readOnlyHint": False},
)
async def write_tracker(
    company: str,
    role: str,
    score: Annotated[float, Field(ge=0.0, le=5.0)],
    status: Annotated[
        str,
        Field(
            description=(
                "Evaluated | CV Sent | Applied | Interview | "
                "Offer | Rejected | Skipped | Withdrawn"
            )
        ),
    ],
    ctx: Context,
    notes: str = "",
    report_markdown: str = "",
) -> dict[str, Any]:
    """Append a job evaluation to the applications tracker (data/applications.md).

    Creates the file with the correct table header if it does not exist.
    If an entry for this company + role combination already exists, its
    status and score are updated in place.

    Args:
        company: Company name (e.g. 'Stripe').
        role: Job title (e.g. 'Senior Solidity Engineer').
        score: Weighted score from the 10-dimension matrix (0.0–5.0).
        status: Canonical status string.
        notes: Short inline note for the table row (optional).
        report_markdown: Full evaluation report to append below the table (optional).
    """
    if status not in _VALID_TRACKER_STATUSES:
        valid = ", ".join(sorted(_VALID_TRACKER_STATUSES))
        raise ToolError(f"Invalid status {status!r}. Valid values: {valid}.")

    project = get_project_dir()
    tracker_path = project / "data" / "applications.md"
    tracker_path.parent.mkdir(parents=True, exist_ok=True)

    today = datetime.date.today().isoformat()
    existing = tracker_path.read_text(encoding="utf-8") if tracker_path.exists() else ""

    lines = existing.splitlines()
    entry_num = 1
    updated = False
    new_lines: list[str] = []

    for line in lines:
        if line.startswith("|") and not line.startswith("| #") and "---" not in line:
            entry_num += 1

        if f"| {company} |" in line and f"| {role} |" in line:
            new_lines.append(
                f"| {entry_num - 1} | {company} | {role} | {score:.1f} "
                f"| {status} | {today} | {notes} |"
            )
            updated = True
        else:
            new_lines.append(line)

    if not existing:
        new_lines = [_TRACKER_HEADER.rstrip()]
        entry_num = 1

    if not updated:
        row = f"| {entry_num} | {company} | {role} | {score:.1f} | {status} | {today} | {notes} |"
        new_lines.append(row)

    content = "\n".join(new_lines)

    if report_markdown.strip():
        report_heading = f"\n\n## {entry_num if not updated else '(updated)'} — {company}: {role}\n\n"
        content += report_heading + report_markdown.strip()

    tracker_path.write_text(content + "\n", encoding="utf-8")

    return {
        "tracker_path": str(tracker_path),
        "entry": entry_num,
        "action": "updated" if updated else "appended",
    }


@mcp.tool(
    title="Write Story Bank",
    annotations={"readOnlyHint": False},
)
async def write_story_bank(
    story_markdown: str,
    ctx: Context,
) -> dict[str, Any]:
    """Append one or more STAR+R stories to data/story-bank.md.

    Creates the file if it does not exist. Stories are appended below
    existing content so the bank accumulates across sessions.

    Args:
        story_markdown: One or more STAR+R stories in Markdown format.
    """
    if not story_markdown.strip():
        raise ToolError("story_markdown is empty.")

    project = get_project_dir()
    story_path = project / "data" / "story-bank.md"
    story_path.parent.mkdir(parents=True, exist_ok=True)

    existing = story_path.read_text(encoding="utf-8") if story_path.exists() else ""

    separator = "\n\n---\n\n" if existing.strip() else ""
    story_path.write_text(
        existing + separator + story_markdown.strip() + "\n",
        encoding="utf-8",
    )

    return {"story_bank_path": str(story_path)}


# Reddit tools (no auth required — uses public JSON API)

@mcp.tool(
    title="Search Reddit",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def search_reddit(
    query: str,
    ctx: Context,
    subreddit: Annotated[
        str | None,
        Field(
            description=(
                "Restrict search to a specific subreddit "
                "(e.g. 'cscareerquestions', 'ExperiencedDevs'). "
                "Omit to search all of Reddit."
            )
        ),
    ] = None,
    sort_by: Annotated[
        str | None,
        Field(description="relevance | hot | top | new | comments"),
    ] = None,
    time_filter: Annotated[
        str | None,
        Field(description="hour | day | week | month | year | all"),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=100)] = 25,
) -> dict[str, Any]:
    """Search Reddit for posts matching a query.

    Use this for salary research, company reviews, interview experiences,
    and job market sentiment. No authentication required.

    Useful subreddits for job search:
    cscareerquestions, ExperiencedDevs, recruitinghell, jobs, webdev,
    programming, devops, startups, remotework, cryptocurrency.

    Args:
        query: Search query (e.g. 'stripe interview experience',
               'senior engineer salary 2026', 'working at google').
        subreddit: Restrict to a specific subreddit.
        sort_by: Sort order for results.
        time_filter: Time range for results.
        limit: Max posts to return (1-100).
    """
    await ctx.report_progress(0, 100, f"Searching Reddit: {query}")

    try:
        result = await _search_reddit(
            query,
            subreddit=subreddit,
            sort=sort_by or "relevance",
            time_filter=time_filter or "all",
            limit=limit,
        )
    except Exception as exc:
        raise ToolError(f"search_reddit: {exc}") from exc

    await ctx.report_progress(100, 100, "Complete")
    return result


@mcp.tool(
    title="Get Reddit Post",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_reddit_post(
    url_or_id: str,
    ctx: Context,
    subreddit: Annotated[
        str | None,
        Field(
            description=(
                "Subreddit name — required only when passing a bare post ID "
                "instead of a full URL."
            )
        ),
    ] = None,
    max_comments: Annotated[int, Field(ge=1, le=200)] = 50,
    comment_sort: Annotated[
        str | None,
        Field(description="top | best | new | controversial | old | qa"),
    ] = None,
) -> dict[str, Any]:
    """Get a Reddit post with its top comments.

    Use this to read full discussion threads — salary negotiations,
    interview reports, company culture discussions, career advice.

    Args:
        url_or_id: Full Reddit post URL or bare post ID.
        subreddit: Required when passing a bare post ID.
        max_comments: Max top-level comments to return (1-200).
        comment_sort: How to sort comments.
    """
    await ctx.report_progress(0, 100, "Fetching Reddit post...")

    try:
        result = await _get_reddit_post(
            url_or_id,
            subreddit=subreddit,
            max_comments=max_comments,
            comment_sort=comment_sort or "top",
        )
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        raise ToolError(f"get_reddit_post: {exc}") from exc

    await ctx.report_progress(100, 100, "Complete")
    return result


@mcp.tool(
    title="Browse Subreddit",
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_reddit_subreddit(
    subreddit: str,
    ctx: Context,
    sort_by: Annotated[
        str | None,
        Field(description="hot | new | top | rising"),
    ] = None,
    time_filter: Annotated[
        str | None,
        Field(description="For 'top' sort only: hour | day | week | month | year | all"),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=100)] = 25,
) -> dict[str, Any]:
    """Browse posts from a subreddit.

    Use this for general subreddit browsing — what's trending in
    r/cscareerquestions this week, top posts in r/ExperiencedDevs, etc.

    Args:
        subreddit: Subreddit name (e.g. 'cscareerquestions', 'webdev').
        sort_by: Sort order — hot, new, top, rising.
        time_filter: Time range (only applies to 'top' sort).
        limit: Max posts to return (1-100).
    """
    await ctx.report_progress(0, 100, f"Browsing r/{subreddit}...")

    try:
        result = await _get_subreddit_posts(
            subreddit,
            sort=sort_by or "hot",
            time_filter=time_filter or "week",
            limit=limit,
        )
    except Exception as exc:
        raise ToolError(f"get_reddit_subreddit: {exc}") from exc

    await ctx.report_progress(100, 100, "Complete")
    return result


# CLI entry point

def cli() -> None:
    """Entry point for the `huntsman-mcp` command."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="huntsman-mcp",
        description="Huntsman MCP server — LinkedIn auditing, resume tailoring, job research.",
    )
    parser.add_argument("--setup", action="store_true", help="Install Patchright Chromium browser")
    parser.add_argument("--login", action="store_true", help="Authenticate with LinkedIn")
    parser.add_argument("--status", action="store_true", help="Check LinkedIn session status")
    parser.add_argument("--version", action="store_true", help="Print version and exit")

    args = parser.parse_args()

    if args.version:
        print(f"huntsman-mcp {__version__}")
        return

    if args.setup:
        _run_setup()
        return

    if args.login:
        asyncio.run(run_login())
        return

    if args.status:
        asyncio.run(print_status())
        return

    # Default: run as MCP server.
    mcp.run()


def _run_setup() -> None:
    """Install the Patchright Chromium browser synchronously."""
    import subprocess

    print("Installing Patchright Chromium browser...")
    try:
        subprocess.run(
            [sys.executable, "-m", "patchright", "install", "chromium"],
            check=True,
        )
        print("Browser installed successfully.")
        print("Next step: run `huntsman-mcp --login` to authenticate with LinkedIn.")
    except subprocess.CalledProcessError as exc:
        print(f"Browser installation failed: {exc}", file=sys.stderr)
        sys.exit(1)
