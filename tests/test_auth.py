"""Tests for LinkedIn auth/session flows."""

import asyncio
import contextlib
import io

import pytest

from huntsman_mcp import auth
from huntsman_mcp.exceptions import BrowserSetupError


class _FakePage:
    def __init__(self, url: str):
        self._url = url

    @property
    def url(self) -> str:
        return self._url

    async def goto(self, *_args, **_kwargs):
        return None

    async def close(self):
        return None


class _FakeContext:
    def __init__(self, page):
        self._page = page

    async def new_page(self):
        return self._page


def test_is_logged_in_propagates_browser_setup_errors(monkeypatch):
    async def fake_get_context(*, headless=True):
        raise BrowserSetupError("launch failed")

    monkeypatch.setattr(auth, "get_context", fake_get_context)

    with pytest.raises(BrowserSetupError, match="launch failed"):
        asyncio.run(auth.is_logged_in())


def test_run_login_warns_when_persisted_session_cannot_be_verified(monkeypatch):
    fake_page = _FakePage("https://www.linkedin.com/feed/")

    async def fake_get_context(*, headless=True):
        return _FakeContext(fake_page)

    async def fake_close_context():
        return None

    async def fake_sleep(_seconds):
        return None

    async def fake_is_logged_in():
        return False

    monkeypatch.setattr(auth, "get_context", fake_get_context)
    monkeypatch.setattr(auth, "close_context", fake_close_context)
    monkeypatch.setattr(auth, "is_logged_in", fake_is_logged_in)
    monkeypatch.setattr(auth.asyncio, "sleep", fake_sleep)

    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        asyncio.run(auth.run_login())

    assert "Login detected." not in stdout.getvalue()
    assert "could not verify the saved session" in stderr.getvalue()


def test_print_status_surfaces_browser_errors(monkeypatch):
    async def fake_is_logged_in():
        raise BrowserSetupError("headless launch failed")

    async def fake_close_context():
        return None

    monkeypatch.setattr(auth, "is_logged_in", fake_is_logged_in)
    monkeypatch.setattr(auth, "close_context", fake_close_context)

    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        with pytest.raises(SystemExit, match="1"):
            asyncio.run(auth.print_status())

    assert "Checking LinkedIn session..." in stdout.getvalue()
    assert "Browser check failed: headless launch failed" in stderr.getvalue()
