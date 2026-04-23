"""Tests for company-page scraping behavior."""

import asyncio

from huntsman_mcp import scraper


class _FakePage:
    def __init__(self):
        self.url = "https://www.linkedin.com/company/stripe/"

    async def close(self):
        return None


class _FakeContext:
    def __init__(self, page):
        self._page = page

    async def new_page(self):
        return self._page


def test_scrape_company_does_not_expand_main_page_controls(monkeypatch):
    fake_page = _FakePage()

    async def fake_get_context():
        return _FakeContext(fake_page)

    async def fake_navigate(_page, _url):
        return None

    def fake_check_page_state(_page, _identifier, *, expected_path_prefix=None):
        return None

    async def fake_scroll(_page):
        return None

    async def fake_expand(_page):
        raise AssertionError("company scrape should not click expand controls on the main page")

    calls = {"count": 0}

    async def fake_page_inner_text(_page, _selector="main"):
        calls["count"] += 1
        if calls["count"] == 1:
            return "Stripe\nFintech infrastructure"
        return "About Stripe\nEconomic infrastructure for the internet"

    monkeypatch.setattr(scraper, "get_context", fake_get_context)
    monkeypatch.setattr(scraper, "_navigate", fake_navigate)
    monkeypatch.setattr(scraper, "_check_page_state", fake_check_page_state)
    monkeypatch.setattr(scraper, "_scroll_to_bottom", fake_scroll)
    monkeypatch.setattr(scraper, "_expand_truncated_content", fake_expand)
    monkeypatch.setattr(scraper, "_page_inner_text", fake_page_inner_text)

    result = asyncio.run(scraper.scrape_company("stripe"))

    assert result["sections"]["main"] == "Stripe\nFintech infrastructure"
    assert result["sections"]["about"] == "About Stripe\nEconomic infrastructure for the internet"
