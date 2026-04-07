"""Reddit public JSON API client — read-only, no auth required.

Uses Reddit's .json endpoints. No OAuth, no API keys, no browser.
Rate limit: ~10 requests/minute enforced by Reddit's edge servers.
A polite User-Agent and 1.5s between requests keeps us well under.
"""

import logging
import re
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx

from huntsman_mcp import __version__

logger = logging.getLogger(__name__)

_REDDIT_BASE = "https://www.reddit.com"
_USER_AGENT = f"huntsman-mcp/{__version__} (github.com/cassxbt/huntsman)"
_REQUEST_TIMEOUT = 15.0

SORT_OPTIONS = frozenset(["relevance", "hot", "top", "new", "comments"])
TIME_FILTERS = frozenset(["hour", "day", "week", "month", "year", "all"])
COMMENT_SORTS = frozenset(["top", "best", "new", "controversial", "old", "qa"])

_SUBREDDIT_RE = re.compile(r"^[A-Za-z0-9_]{1,50}$")


def _validate_subreddit(name: str) -> str:
    """Validate and return the subreddit name. Raises ValueError if invalid."""
    name = name.strip().removeprefix("r/").removeprefix("R/")
    if not _SUBREDDIT_RE.match(name):
        raise ValueError(
            f"Invalid subreddit name {name!r}. "
            "Subreddit names contain only letters, numbers, and underscores."
        )
    return name


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": _USER_AGENT},
        timeout=_REQUEST_TIMEOUT,
        follow_redirects=True,
    )


def _parse_post(post: dict) -> dict[str, Any]:
    return {
        "title": post.get("title", ""),
        "subreddit": post.get("subreddit", ""),
        "author": post.get("author", ""),
        "score": post.get("score", 0),
        "upvote_ratio": post.get("upvote_ratio", 0),
        "num_comments": post.get("num_comments", 0),
        "url": f"{_REDDIT_BASE}{post.get('permalink', '')}",
        "selftext": post.get("selftext", "")[:3000],
        "created_utc": post.get("created_utc", 0),
        "id": post.get("id", ""),
        "is_self": post.get("is_self", False),
        "link_flair_text": post.get("link_flair_text"),
    }


def _parse_comment(c: dict) -> dict[str, Any]:
    return {
        "author": c.get("author", ""),
        "body": c.get("body", "")[:2000],
        "score": c.get("score", 0),
        "created_utc": c.get("created_utc", 0),
        "is_submitter": c.get("is_submitter", False),
    }


async def search_reddit(
    query: str,
    *,
    subreddit: str | None = None,
    sort: str = "relevance",
    time_filter: str = "all",
    limit: int = 25,
) -> dict[str, Any]:
    """Search Reddit posts.

    Args:
        query: Search query string.
        subreddit: Restrict to a specific subreddit.
        sort: Sort order — relevance, hot, top, new, comments.
        time_filter: Time range — hour, day, week, month, year, all.
        limit: Max results (1-100).

    Returns:
        Dict with query echo, post list, and result count.
    """
    limit = max(1, min(100, limit))
    sort = sort if sort in SORT_OPTIONS else "relevance"
    time_filter = time_filter if time_filter in TIME_FILTERS else "all"

    if subreddit:
        subreddit = _validate_subreddit(subreddit)

    params: dict[str, str] = {
        "q": query,
        "sort": sort,
        "t": time_filter,
        "limit": str(limit),
        "restrict_sr": "on" if subreddit else "off",
    }

    if subreddit:
        base_url = f"{_REDDIT_BASE}/r/{subreddit}/search.json"
    else:
        base_url = f"{_REDDIT_BASE}/search.json"

    url = f"{base_url}?{urlencode(params)}"
    logger.info("search_reddit: query=%r subreddit=%s sort=%s", query, subreddit, sort)

    async with _make_client() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

    posts = [
        _parse_post(child["data"])
        for child in data.get("data", {}).get("children", [])
        if child.get("kind") == "t3"
    ]

    return {
        "query": query,
        "subreddit": subreddit,
        "sort": sort,
        "time_filter": time_filter,
        "result_count": len(posts),
        "posts": posts,
    }


async def get_reddit_post(
    url_or_id: str,
    *,
    subreddit: str | None = None,
    max_comments: int = 50,
    comment_sort: str = "top",
) -> dict[str, Any]:
    """Get a Reddit post with its top comments.

    Args:
        url_or_id: Full Reddit URL or post ID.
        subreddit: Required when passing a bare post ID.
        max_comments: Max top-level comments to return (1-200).
        comment_sort: Sort comments by: top, best, new, controversial, old, qa.

    Returns:
        Dict with full post content and comment list.

    Raises:
        ValueError: If bare ID passed without subreddit.
        httpx.HTTPStatusError: On non-2xx response.
    """
    max_comments = max(1, min(200, max_comments))
    comment_sort = comment_sort if comment_sort in COMMENT_SORTS else "top"

    if url_or_id.startswith("http"):
        parsed = urlparse(url_or_id)
        if parsed.hostname not in ("reddit.com", "www.reddit.com"):
            raise ValueError(
                f"Invalid URL {url_or_id!r}. Only reddit.com URLs are accepted."
            )
        if not re.match(r"^/r/[A-Za-z0-9_]+/comments/", parsed.path):
            raise ValueError(
                f"URL {url_or_id!r} does not point to a Reddit thread. "
                "Expected: reddit.com/r/{subreddit}/comments/{id}/..."
            )
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        json_url = f"{clean}.json?sort={comment_sort}&limit={max_comments}"
    else:
        if not subreddit:
            raise ValueError(
                "subreddit is required when passing a bare post ID. "
                "Pass the full URL or specify the subreddit parameter."
            )
        subreddit = _validate_subreddit(subreddit)
        json_url = (
            f"{_REDDIT_BASE}/r/{subreddit}/comments/{url_or_id}.json"
            f"?sort={comment_sort}&limit={max_comments}"
        )

    logger.info("get_reddit_post: url=%s", json_url)

    async with _make_client() as client:
        response = await client.get(json_url)
        response.raise_for_status()
        data = response.json()

    if not isinstance(data, list) or len(data) < 2:
        return {"error": "Unexpected Reddit API response format", "raw_url": json_url}

    post_data = data[0]["data"]["children"][0]["data"]
    post = _parse_post(post_data)
    post["selftext"] = post_data.get("selftext", "")  # Full text for single post view.

    comments = [
        _parse_comment(child["data"])
        for child in data[1].get("data", {}).get("children", [])
        if child.get("kind") == "t1"
    ]

    return {
        "post": post,
        "comments": comments,
        "comment_count_returned": len(comments),
    }


async def get_subreddit_posts(
    subreddit: str,
    *,
    sort: str = "hot",
    time_filter: str = "week",
    limit: int = 25,
) -> dict[str, Any]:
    """Get posts from a subreddit.

    Args:
        subreddit: Subreddit name (e.g. 'cscareerquestions').
        sort: Sort order — hot, new, top, rising.
        time_filter: For 'top' sort only — hour, day, week, month, year, all.
        limit: Max posts (1-100).

    Returns:
        Dict with subreddit name, post list, and result count.
    """
    subreddit = _validate_subreddit(subreddit)
    limit = max(1, min(100, limit))
    sort = sort if sort in {"hot", "new", "top", "rising"} else "hot"
    time_filter = time_filter if time_filter in TIME_FILTERS else "week"

    params: dict[str, str] = {"limit": str(limit)}
    if sort == "top":
        params["t"] = time_filter

    url = f"{_REDDIT_BASE}/r/{subreddit}/{sort}.json?{urlencode(params)}"
    logger.info("get_subreddit_posts: r/%s sort=%s", subreddit, sort)

    async with _make_client() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

    posts = [
        _parse_post(child["data"])
        for child in data.get("data", {}).get("children", [])
        if child.get("kind") == "t3"
    ]

    return {
        "subreddit": subreddit,
        "sort": sort,
        "time_filter": time_filter if sort == "top" else None,
        "result_count": len(posts),
        "posts": posts,
    }
