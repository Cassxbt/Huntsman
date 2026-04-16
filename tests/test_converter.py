"""Golden tests for the resume Markdown sanitizer and HTML builder."""

import pytest
from huntsman_mcp.converter import _sanitize, _build_html, _link_sub
import re

# ---------------------------------------------------------------------------
# _sanitize
# ---------------------------------------------------------------------------

class TestSanitize:
    def test_strips_bold(self):
        assert _sanitize("**Senior Engineer**") == "Senior Engineer"

    def test_strips_italic(self):
        assert _sanitize("*Senior Engineer*") == "Senior Engineer"

    def test_strips_bold_italic(self):
        assert _sanitize("***Senior Engineer***") == "Senior Engineer"

    def test_strips_inline_code(self):
        assert _sanitize("`python`") == "python"

    def test_strips_markdown_heading(self):
        assert _sanitize("## Work Experience").strip() == "Work Experience"

    def test_strips_horizontal_rule(self):
        result = _sanitize("---")
        assert result.strip() == ""

    def test_strips_html_tags(self):
        assert _sanitize("<br>text</br>") == "text"

    def test_strips_image(self):
        assert _sanitize("![alt](https://example.com/img.png)") == ""

    def test_strips_fenced_code_block(self):
        md = "```python\nprint('hello')\n```"
        assert "```" not in _sanitize(md)
        assert "print" in _sanitize(md)

    def test_preserves_plain_text(self):
        text = "Architected payment pipeline reducing p99 latency by 40%."
        assert _sanitize(text) == text

    def test_preserves_pipe_characters(self):
        line = "Senior Engineer | Stripe | Full-time | Jan 2023 – Present"
        assert _sanitize(line) == line

    def test_preserves_bullet_prefix(self):
        line = "- Built a distributed caching layer serving 50k RPS."
        assert _sanitize(line) == line

    def test_handles_empty_string(self):
        assert _sanitize("") == ""

    def test_handles_multiple_blank_lines(self):
        result = _sanitize("\n\n\n")
        assert result.strip() == ""


# ---------------------------------------------------------------------------
# _link_sub (the Markdown link handler)
# ---------------------------------------------------------------------------

_RE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]*)\)")

def _apply_link_sub(text: str) -> str:
    return _RE_LINK.sub(_link_sub, text)


class TestLinkSub:
    def test_generic_label_keeps_url(self):
        # Label is generic — URL provides the context.
        result = _apply_link_sub("[GitHub](https://github.com/cassxbt)")
        assert "github.com/cassxbt" in result

    def test_label_is_url_drops_url(self):
        # Label IS the URL — redundant to show both.
        result = _apply_link_sub("[github.com/cassxbt](https://github.com/cassxbt)")
        assert "github.com/cassxbt" in result
        assert "https://" not in result

    def test_handle_matches_url_drops_url(self):
        # Twitter handle embedded in URL — label alone is sufficient.
        result = _apply_link_sub("[cassxbt](https://twitter.com/cassxbt)")
        assert result == "cassxbt"

    def test_meaningful_label_preserves_url(self):
        # Label and URL are semantically different — show both.
        result = _apply_link_sub("[My Portfolio](https://cassxbt.dev)")
        assert "My Portfolio" in result
        assert "cassxbt.dev" in result


# ---------------------------------------------------------------------------
# _build_html (structural smoke tests — not pixel-perfect)
# ---------------------------------------------------------------------------

SAMPLE_RESUME = """\
Jane Smith
jane@example.com | github.com/janesmith

WORK EXPERIENCE
Senior Engineer | Stripe | Full-time | Jan 2023 – Present
- Architected a payment reconciliation system processing $2B/month.
- Tech: Python, Kubernetes, PostgreSQL

TECHNICAL SKILLS
Languages: Python, Go, TypeScript
Infrastructure: Kubernetes, Terraform, AWS

EDUCATION
BSc Computer Science | MIT | 2018
"""


class TestBuildHtml:
    def setup_method(self):
        self.html = _build_html(SAMPLE_RESUME)

    def test_name_rendered(self):
        assert "Jane Smith" in self.html

    def test_contact_rendered(self):
        assert "jane@example.com" in self.html

    def test_section_header_rendered(self):
        assert "WORK EXPERIENCE" in self.html
        assert "section-head" in self.html

    def test_entry_title_rendered(self):
        assert "Senior Engineer" in self.html
        assert "entry-title" in self.html

    def test_bullet_rendered_as_li(self):
        assert "<li>" in self.html
        assert "Architected" in self.html

    def test_tech_line_rendered(self):
        assert "tech" in self.html
        assert "Kubernetes" in self.html

    def test_skill_row_rendered(self):
        assert "skill-row" in self.html
        assert "Languages" in self.html

    def test_no_markdown_artifacts(self):
        assert "**" not in self.html
        assert "```" not in self.html
        assert "##" not in self.html

    def test_valid_html_structure(self):
        assert self.html.startswith("<!DOCTYPE html>")
        assert "</html>" in self.html
        assert "<body>" in self.html
        assert "</body>" in self.html
