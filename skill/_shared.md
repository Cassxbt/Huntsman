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

The agent maintains `data/applications.md` as a running log of all evaluated jobs.

Table format:
```markdown
| # | Company | Role | Score | Status | Date | Report |
|---|---------|------|-------|--------|------|--------|
| 1 | Acme Corp | Senior Engineer | 4.2 | Evaluated | 2026-01-15 | See below |
```

Canonical statuses: `Evaluated`, `CV Sent`, `Applied`, `Interview`, `Offer`, `Rejected`, `Skipped`, `Withdrawn`.

Rules:
- Append new entries. Never reorder or delete existing entries.
- Dedup by company + role. If the same job is evaluated twice, update the existing row.
- Report content goes below the table under a `## #N — Company: Role` heading.
