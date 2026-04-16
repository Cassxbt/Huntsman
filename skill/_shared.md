# Shared Rules — Scoring, ATS, and Global Constraints

This file is read by all modes. Do not duplicate these rules in mode files.

---

## Scoring Matrix (10 dimensions)

Every job evaluation produces a weighted score from 0.0 to 5.0.

| Dimension | Weight | What it measures |
|---|---|---|
| North Star alignment | 25% | Does this role move you toward your stated career goal? |
| CV match | 15% | What percentage of hard requirements do you actually meet? |
| Level fit | 15% | Is the seniority right — not too junior, not an unrealistic stretch? |
| Compensation | 10% | Is the stated or estimated pay within your target range? |
| Growth trajectory | 10% | Does this role open doors to where you want to be in 2 years? |
| Remote quality | 5% | Is the remote setup real (async-first) or performative (camera-on 9-5)? |
| Company reputation | 5% | Would this name strengthen your resume? |
| Tech stack modernity | 5% | Is the stack current, or will you be maintaining legacy? |
| Speed to offer | 5% | How many rounds? Is the process known to be fast or glacial? |
| Cultural signals | 5% | Red flags or green flags from JD language, Glassdoor, Reddit? |

**Scoring rules:**
- Each dimension scores 0.0–5.0 independently
- Final score = weighted sum of all dimensions
- Score < 3.0 → SKIP recommendation (agent explains why)
- Score 3.0–4.4 → EVALUATE (generate report + tailored CV only)
- Score >= 4.5 → FULL PIPELINE (report + CV + outreach draft + interview prep)

**Hard-no penalty:** If a job matches any `hard_nos` from profile.yml, apply a -1.0 penalty to the final score and flag the specific hard-no that triggered it.

---

## Decision Gates

The agent must not generate application materials for jobs scoring below 3.0 unless the user explicitly overrides. This is the quality-over-volume constraint.

```
Score < 3.0  → "This scores [X]. I recommend skipping. Here's why: [reasons]. Override?"
Score 3.0–4.4 → Generate evaluation report + tailored CV
Score >= 4.5  → Full pipeline: report + CV + outreach + interview prep
```

---

## ATS Rules (non-negotiable for all resume output)

1. Single-column layout. No sidebars, no two-column designs.
2. Standard section headers only: Professional Summary, Technical Skills, Work Experience, Projects, Education, Certifications, Awards.
3. No images, icons, or graphics with text in them.
4. No nested tables. Simple structure only.
5. UTF-8 selectable text throughout.
6. Keywords distributed across: Summary (top 5), first bullet of each role, Skills section.
7. 60–80% keyword match with the target JD.
8. 15–25 keywords total. No single keyword repeated more than 4–5 times.
9. Every bullet: [Strong Verb] + [What] + [Quantified Result].
10. No em dashes. No AI-pattern language.
11. Roles and projects in reverse-chronological order (most recent first). Never reorder by relevance.
12. Consistent date format throughout: "Month YYYY – Month YYYY" (e.g., "Jan 2023 – Mar 2025"). Never mix formats within the same document.
13. **Format by submission method:**
    - ATS portal (Greenhouse, Lever, Workday, iCIMS, Taleo) → DOCX. These systems parse DOCX natively and more reliably than PDF.
    - Direct email to a human or LinkedIn message → PDF. Preserves layout exactly.
    - LinkedIn Easy Apply → PDF. LinkedIn renders PDFs cleanly in its viewer.
    - When in doubt: ask the user how they are submitting before converting.

---

## Language Constraints (apply to ALL generated text)

Never use these words or phrases:
leverage, utilize, spearhead, overarching, robust, seamless, cutting-edge, innovative,
synergy, dynamic, transformative, impactful, delve, harness, passionate about,
dedicated professional, gaps, precision, directly applies, compelling, nuanced.

No em dashes. Use commas or restructure the sentence.

Write like a senior engineer talking about their own work. Short sentences. Specific.
If it sounds like a LinkedIn post or a ChatGPT output, rewrite it.

---

## Profile Awareness

At the start of every session, silently check for `config/profile.yml`:

- **If it exists:** Read it. Use the user's name, target roles, tech stack, comp targets, hard-nos, hero metrics, and exit story throughout all evaluations and generated content.
- **If it does not exist:** Run the onboarding flow (defined in SKILL.md) before doing any evaluation work. Copy `config/profile.example.yml` to `config/profile.yml` and fill it in from the user's answers.

Also check for `cv.md` in the project root:

- **If it exists:** Use it as the source of truth for what the user has actually done. Never fabricate credentials not present in cv.md.
- **If it does not exist:** Ask the user to describe their experience or paste their current resume. Save it as `cv.md` for future sessions.

---

## Environment Variable

Resume conversion output defaults to `~/Downloads/`. Override with the `HUNTSMAN_OUTPUT_DIR` environment variable.

---

## Tracker Format

After every evaluation, call `write_tracker(company, role, score, status, notes, report_markdown)`.
Never write to `data/applications.md` directly — the tool handles dedup and formatting.

Canonical statuses: `Evaluated`, `CV Sent`, `Applied`, `Interview`, `Offer`, `Rejected`, `Skipped`, `Withdrawn`.

Pass the full evaluation report (Blocks A-D output) as `report_markdown`.
Pass a one-line summary as `notes` for the table row.
