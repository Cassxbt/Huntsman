"""Shared Patchright browser context with persistent session storage.

Single async context is created on first use and reused across all tool calls.
Session data (cookies, localStorage) is persisted via Chromium's persistent
profile directory — no manual cookie export required.
"""

import asyncio
import logging

from patchright.async_api import BrowserContext, Playwright, async_playwright

from huntsman_mcp.config import BROWSER_PROFILE_DIR
from huntsman_mcp.exceptions import BrowserSetupError

logger = logging.getLogger(__name__)

_playwright: Playwright | None = None
_context: BrowserContext | None = None
_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock


def _is_context_alive(ctx: BrowserContext) -> bool:
    """Check whether the context is still usable without making a network call."""
    try:
        # Accessing .pages is a synchronous property; raises if context is closed.
        _ = ctx.pages
        return True
    except Exception:
        return False


async def _safe_close() -> None:
    """Tear down the global context and Playwright instance without raising."""
    global _playwright, _context
    for obj, method in ((_context, "close"), (_playwright, "stop")):
        if obj is not None:
            try:
                await getattr(obj, method)()
            except Exception:
                pass
    _playwright = None
    _context = None


async def get_context(*, headless: bool = True) -> BrowserContext:
    """Return the shared persistent browser context, creating it if needed.

    Args:
        headless: Pass False only during the interactive login flow.

    Raises:
        BrowserSetupError: If Patchright Chromium is not installed or fails to start.
    """
    global _playwright, _context

    async with _get_lock():
        if _context is not None:
            if _is_context_alive(_context):
                return _context
            # Context died (e.g. browser crashed). Tear down and recreate.
            logger.warning("Browser context died unexpectedly; recreating.")
            await _safe_close()

        BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

        try:
            _playwright = await async_playwright().start()
            _context = await _playwright.chromium.launch_persistent_context(
                user_data_dir=str(BROWSER_PROFILE_DIR),
                headless=headless,
                # Reduce bot-detection surface.
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
                locale="en-US",
                timezone_id="America/New_York",
                # Realistic viewport.
                viewport={"width": 1280, "height": 800},
            )
        except Exception as exc:
            await _safe_close()
            raise BrowserSetupError(
                f"Failed to launch Patchright Chromium: {exc}\n"
                "Run `huntsman-mcp --setup` to install the browser."
            ) from exc

        logger.debug("Browser context created (headless=%s)", headless)
        return _context


async def close_context() -> None:
    """Gracefully close the shared context. Safe to call multiple times."""
    async with _get_lock():
        await _safe_close()
