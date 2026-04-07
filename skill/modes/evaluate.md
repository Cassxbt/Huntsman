# Mode: Evaluate Job

Triggered when the user provides a job URL, job ID, or pastes a job description.
This is the core intelligence engine. Every evaluation follows the same A-F block structure.

---

## Prerequisites

Before running blocks A-F, gather all inputs:

1. **Job data:** Call `get_linkedin_job(job_id)` or use the pasted JD text.
2. **Company data:** Call `get_linkedin_company(company_identifier)` using the company name extracted from the job posting.
3. **Profile:** Read `config/profile.yml`. If missing, stop and run onboarding (see SKILL.md).
4. **CV:** Read `cv.md`. If missing, ask the user to provide their experience.
5. **Reddit enrichment (optional):** Call `search_reddit("{company_name} interview experience")` and `search_reddit("{company_name} salary {role_level}", subreddit="cscareerquestions")` to pull real-world data. Skip if the company is too small or obscure to have Reddit presence.

---

## Block A — Role Summary

Produce a structured summary table from the raw JD text:

```
ROLE SUMMARY
Company:        [name]
Title:          [exact title from JD]
Archetype:      [builder / researcher / leader / specialist / generalist]
Domain:         [industry / vertical]
Function:       [what the person actually does day-to-day]
Seniority:      [junior / mid / senior / staff / principal / lead / manager / director]
Remote:         [full remote / hybrid / on-site / unclear]
Team size:      [if mentioned, otherwise "not stated"]
Comp range:     [if stated, otherwise estimate from Reddit/market data]
TL;DR:          [one sentence — what this role actually is in plain English]
```

---

## Block B — CV Match

Map every requirement from the JD against the user's cv.md, line by line.

```
REQUIREMENT MATCH
| JD Requirement | CV Evidence | Match |
|---|---|---|
| "5+ years Python" | "cv.md line 23: Python development since 2021 (5 years)" | MATCH |
| "Kubernetes at scale" | No evidence in CV | GAP |
| "Team leadership" | "cv.md line 45: Led 3-person team on PaymentAPI" | PARTIAL |
```

After the table:
- **Match rate:** X/Y requirements met (Z%)
- **Hard gaps:** Requirements that cannot be credibly addressed — these are blockers
- **Soft gaps:** Requirements that can be mitigated with adjacent experience, side projects, or quick learning. For each soft gap, provide a specific mitigation sentence the user could use in a cover letter or interview.
- **Over-qualified signals:** Requirements significantly below the user's actual level — flag these as they affect Level fit scoring.

---

## Block C — Level Strategy

Compare the JD's seniority expectations against the user's actual level (from profile.yml archetype + cv.md experience).

- **If aligned:** State this briefly and move on.
- **If the role is below the user's level:** Flag it. Suggest how to frame the application as a strategic move (e.g., "joining early to grow into a lead role") rather than a step down.
- **If the role is above the user's level:** Flag it honestly. Suggest specific framing: which achievements to emphasize, what language to use, what the user should prepare to address in an interview. Include a 90-day proof plan the user could reference.

---

## Block D — Compensation Research

Use multiple sources:
1. **JD stated range** — if present, use it.
2. **Reddit data** — pull from `search_reddit` results (salary threads, offer reports).
3. **LinkedIn company context** — company size, funding stage, and domain from `get_linkedin_company`.
4. **Market estimate** — if no hard data, estimate based on role level + domain + location.

Output:
```
COMPENSATION ANALYSIS
Stated range:    [from JD or "not stated"]
Reddit signal:   [summary of any salary data points found, with links]
Market estimate: [$X–$Y based on {reasoning}]
vs. user target: [above / within / below user's preferred range from profile.yml]
Negotiation note: [one specific data point the user could cite in negotiation]
```

---

## Scoring (run AFTER Block D, BEFORE Blocks E and F)

After completing blocks A-D, score the job using the 10-dimension weighted matrix from `_shared.md`. The score determines whether to proceed with Blocks E and F.

```
SCORE BREAKDOWN
North Star alignment (25%): 4.0 — [one-line justification]
CV match (15%):             3.5 — [X/Y requirements met]
Level fit (15%):            4.5 — [aligned / stretch / overqualified]
Compensation (10%):         3.0 — [within range / below / above]
Growth trajectory (10%):    4.0 — [opens doors to X]
Remote quality (5%):        5.0 — [async-first confirmed]
Company reputation (5%):    3.5 — [known / unknown / mixed]
Tech stack modernity (5%):  4.0 — [current / legacy / mixed]
Speed to offer (5%):        3.0 — [fast / unknown / known slow]
Cultural signals (5%):      3.5 — [green flags / red flags / neutral]

FINAL SCORE: 3.85 / 5.0
RECOMMENDATION: EVALUATE — generate tailored CV
```

Apply hard-no penalty if applicable. Then follow the decision gates from `_shared.md`:

- **Score < 3.0** — STOP. Present the report (Blocks A-D) and recommend skipping. Do not proceed to Blocks E or F. Ask: "This scores [X]. I recommend skipping. Here's why: [reasons]. Override?"
- **Score 3.0-4.4** — Proceed to Block E (CV personalization). Skip Block F.
- **Score >= 4.5** — Proceed to both Block E and Block F.

---

## Block E — CV Personalization Plan (score >= 3.0 only)

Based on blocks B and C, produce specific changes to make to the user's cv.md for this application:

1. **Professional Summary rewrite** — echo the JD's exact language and priorities.
2. **Skills reorder** — move the JD's priority technologies to the top.
3. **Project selection** — which 4-5 projects from cv.md best demonstrate the required skills? List them in recommended order.
4. **Bullet adjustments** — for each selected project, which bullet should be rewritten and how? Be specific: "Change line 47 from [current] to [proposed]."
5. **Keyword injection** — list any JD keywords not yet present in cv.md that should be added, and where.

Do not fabricate. Every change must be grounded in real experience from cv.md. If a keyword is not something the user has done, do not inject it.

After producing the plan: generate the tailored CV in Markdown and call `convert_resume` to produce the output file. Ask the user for format preference (PDF or DOCX) first.

---

## Block F — Interview Prep (score >= 4.5 only)

This block only runs for high-scoring jobs. For the full interview prep workflow, read `skill/modes/interview.md`.

Generate 4-6 STAR+R stories mapped to the JD's key requirements.

STAR+R format:
- **Situation:** Context and constraints (1-2 sentences)
- **Task:** What you specifically needed to accomplish
- **Action:** What you did — technical detail, decisions made, tools used
- **Result:** Quantified outcome
- **Reflection:** What you learned or would do differently — this signals seniority

Rules:
- Every story must map to a specific JD requirement. State the mapping explicitly.
- Stories must come from real experience in cv.md. Do not invent scenarios.
- If the user's story bank exists (`data/story-bank.md`), check for existing stories that apply before generating new ones. Reuse and refine, don't regenerate.
- Append any new stories to `data/story-bank.md` for future sessions.

---

## Block G — Outreach (score >= 4.5 only)

High-scoring jobs get the full pipeline. After interview prep, run outreach to the hiring manager.

Read `skill/modes/outreach.md` and follow the full procedure:
1. Find the hiring manager or recruiter via `search_linkedin_people`
2. Pull their profile via `get_linkedin_profile`
3. Draft a 300-character connection message with a specific hook, proof point, and CTA
4. Draft a follow-up sequence (2 messages max)
5. Draft a cold email if contact info is available

Present the outreach package alongside the interview prep and tailored CV.

---

## Tracker Update

After completing the evaluation (regardless of score), append a row to `data/applications.md` and write the full report below the table. Follow the tracker format defined in `_shared.md`.
