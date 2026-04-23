"""LinkedIn session management and interactive login flow.

Session data is persisted automatically by Patchright's persistent context
(stored in BROWSER_PROFILE_DIR). No manual cookie handling required.
"""

import asyncio
import logging
import sys
import time

from huntsman_mcp.browser import close_context, get_context
from huntsman_mcp.config import LI_BASE
from huntsman_mcp.exceptions import AuthRequired, BrowserSetupError

logger = logging.getLogger(__name__)

_FEED_URL = f"{LI_BASE}/feed/"
_LOGIN_URL = f"{LI_BASE}/login"
_CHECK_TIMEOUT_MS = 20_000

# Cache the session check result so we don't navigate to /feed/ on every
# tool call. 5 minutes is conservative — LinkedIn sessions last weeks.
_SESSION_TTL = 300.0
_session_valid_until: float = 0.0


def _looks_logged_in_url(url: str) -> bool:
    """Return True when the current LinkedIn URL indicates an authenticated session."""
    return "feed" in url and "authwall" not in url and "login" not in url


async def is_logged_in() -> bool:
    """Return True if the stored session is still valid.

    Opens a page, navigates to the LinkedIn feed, and checks the resulting URL.
    Closes the page before returning.
    """
    try:
        ctx = await get_context()
        page = await ctx.new_page()
        try:
            await page.goto(_FEED_URL, wait_until="domcontentloaded", timeout=_CHECK_TIMEOUT_MS)
            await asyncio.sleep(1.0)
            url = page.url
            return _looks_logged_in_url(url)
        finally:
            await page.close()
    except BrowserSetupError:
        raise
    except Exception as exc:
        logger.debug("Session check failed: %s", exc)
        return False


async def ensure_logged_in() -> None:
    """Raise AuthRequired if no valid session exists.

    Result is cached for _SESSION_TTL seconds to avoid a full /feed/ navigation
    on every tool call. The cache is invalidated whenever run_login() completes.
    """
    global _session_valid_until
    if time.monotonic() < _session_valid_until:
        return  # Recently verified — skip the network round-trip.

    if not await is_logged_in():
        _session_valid_until = 0.0
        raise AuthRequired(
            "No valid LinkedIn session found. "
            "Run `huntsman-mcp --login` to authenticate."
        )

    _session_valid_until = time.monotonic() + _SESSION_TTL


async def run_login() -> None:
    """Open a visible Chromium browser for interactive LinkedIn login.

    Waits for the user to complete login (detected by reaching /feed/),
    then closes the visible browser. The session is automatically persisted
    in the browser profile directory for future headless use.
    """
    # Close any existing headless context before opening a visible one.
    # Both modes share the same profile dir, so they can't run simultaneously.
    await close_context()

    print("\nhuntsman-mcp: Opening LinkedIn login window...")

    ctx = await get_context(headless=False)
    page = await ctx.new_page()

    try:
        await page.goto(_LOGIN_URL, wait_until="domcontentloaded")
    except Exception as exc:
        await page.close()
        await close_context()
        print(f"Failed to open LinkedIn login page: {exc}", file=sys.stderr)
        return

    print("Sign in to LinkedIn in the browser window that just opened.")
    print("This window will close automatically once login is detected.")
    print("(Or press Ctrl+C here to cancel.)\n")

    login_detected = False

    try:
        # Poll for up to 5 minutes for a successful login.
        for _ in range(300):
            await asyncio.sleep(1.0)
            try:
                url = page.url
            except Exception:
                # Page was closed externally.
                break
            if _looks_logged_in_url(url):
                login_detected = True
                break
        else:
            print(
                "Login timeout: 5 minutes elapsed without detecting a successful login.",
                file=sys.stderr,
            )
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nLogin cancelled.")
    finally:
        try:
            await page.close()
        except Exception:
            pass
        # Close the visible context. Session is already persisted in the profile dir.
        await close_context()

    # Reset the cache so the next tool call re-verifies the fresh session.
    global _session_valid_until
    _session_valid_until = 0.0

    if login_detected:
        try:
            if await is_logged_in():
                print("Login detected. Session saved and verified.")
            else:
                print(
                    "Login detected, but Huntsman could not verify the saved session after "
                    "closing the browser. Run `huntsman-mcp --status` in a few seconds. "
                    "If it still fails, rerun `huntsman-mcp --login`.",
                    file=sys.stderr,
                )
        except BrowserSetupError as exc:
            print(
                "Login detected, but Huntsman could not verify the saved session automatically: "
                f"{exc}",
                file=sys.stderr,
            )
        finally:
            await close_context()

    print("Run `huntsman-mcp --status` to verify the session is active.\n")


async def print_status() -> None:
    """Print the current authentication status to stdout."""
    print("Checking LinkedIn session...", end=" ", flush=True)
    try:
        logged_in = await is_logged_in()
    except BrowserSetupError as exc:
        print(f"Browser check failed: {exc}", file=sys.stderr)
        await close_context()
        raise SystemExit(1) from exc
    else:
        if logged_in:
            print("Active. Session is valid.")
        else:
            print("Not logged in. Run `huntsman-mcp --login` to authenticate.")
        await close_context()
