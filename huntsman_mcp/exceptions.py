"""Exception hierarchy for huntsman-mcp.

All exceptions surface as user-facing ToolError messages.
Keep messages actionable — tell the user exactly what to do next.
"""


class HuntsmanError(Exception):
    """Base class for all huntsman-mcp errors."""


class BrowserSetupError(HuntsmanError):
    """Patchright browser is not installed or failed to launch.

    Fix: run `huntsman-mcp --setup`
    """


class AuthRequired(HuntsmanError):
    """No valid LinkedIn session. User must log in.

    Fix: run `huntsman-mcp --login`
    """


class SessionExpired(AuthRequired):
    """LinkedIn session token has expired.

    Fix: run `huntsman-mcp --login` to re-authenticate.
    """


class RateLimited(HuntsmanError):
    """LinkedIn is throttling requests.

    Fix: wait a few minutes before retrying.
    """


class ProfileNotFound(HuntsmanError):
    """No LinkedIn profile or page exists at the requested URL."""


class PrivateProfile(HuntsmanError):
    """Profile exists but is private — content is not publicly accessible."""


class ScrapingError(HuntsmanError):
    """Unexpected failure during page scraping."""


class NavigationError(ScrapingError):
    """Page navigation timed out or produced an unexpected URL."""
