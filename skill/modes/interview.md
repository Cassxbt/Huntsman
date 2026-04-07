# Mode: Interview Prep

Triggered when the user asks to prepare for an interview, or automatically as Block F
of the evaluation pipeline when a job scores >= 4.5.

Before executing, read `skill/_shared.md` for language constraints and banned word lists.
All generated text (stories, tips) must follow those rules.

---

## Prerequisites

1. **Evaluation report:** If one exists for this role (check `data/applications.md`), use it. The JD requirements and CV match analysis from blocks A-B are the foundation for story selection.
2. **Story bank:** Read `data/story-bank.md` if it exists. Check for reusable stories before generating new ones.
3. **Profile:** Read `config/profile.yml` for archetype and hero metrics.
4. **CV:** Read `cv.md` for real experience to draw stories from.

---

## Story Generation — STAR+R Format

For each key JD requirement, produce a mapped story:

```
STORY: [Short title]
Maps to: [Exact JD requirement this addresses]

Situation: [Context and constraints — where, when, what was the problem. 1-2 sentences.]
Task: [What you specifically needed to accomplish. 1 sentence.]
Action: [What you did. Technical specifics: tools, decisions, tradeoffs. 2-4 sentences.]
Result: [Quantified outcome. Numbers, percentages, users, revenue, time saved. 1-2 sentences.]
Reflection: [What you learned, what you would do differently, or how this shaped your approach. 1-2 sentences.]
```

---

## Rules

- Generate 4-6 stories per evaluation. Cover the top requirements from the JD.
- Every story must be grounded in real experience from cv.md. Do not invent.
- The Reflection component is what separates senior from junior answers. Always include it.
- If a story from the bank already covers a requirement, reuse it with minor adaptation to echo the JD's specific language. Do not regenerate from scratch.
- Vary the stories across different projects and time periods. Do not pull 4 stories from the same project.
- For each story, include a one-line note on when to use it: "Use this when asked about: [typical interview question patterns]."

---

## Archetype-Specific Framing

Adapt the tone of stories based on the user's archetype from profile.yml:

- **Builder:** Emphasize shipping, iteration speed, pragmatic tradeoffs.
- **Researcher:** Emphasize depth of investigation, methodology, novel approaches.
- **Leader:** Emphasize coordination, mentoring, decision-making under uncertainty.
- **Specialist:** Emphasize domain expertise, edge-case handling, deep technical knowledge.
- **Generalist:** Emphasize breadth, learning speed, connecting disparate systems.

---

## Company-Specific Angles

If an evaluation report exists for this role, use the research mode's culture signals:

- What does this company value? Frame stories to emphasize those values.
- What language do they use? Mirror it in how you describe your actions and results.
- What problems are they likely facing? (Infer from JD + company stage + domain.) Lead with stories that show you've solved similar problems.

---

## Reddit Intelligence

If interview process data was gathered in the research mode, surface it:

- Known interview format (coding, system design, behavioral, take-home)
- Typical questions reported by candidates
- Red flags or positive signals from the process
- Timeline expectations

If no prior research exists, run: `search_reddit("{company_name} interview process", subreddit="cscareerquestions", sort_by="top", time_filter="year", limit=5)`.

---

## Story Bank Management

After generating stories, update `data/story-bank.md`:

```markdown
## [Story Title]
Added: [date]
Last used for: [Company — Role]
Maps to: [requirement category]

[Full STAR+R content]
```

Rules:
- Do not duplicate stories already in the bank. Update the "Last used for" field instead.
- If a story is refined for a new role, update the content in place.
- The bank should converge on 8-12 master stories over time. Quality over quantity.
- If the bank exceeds 15 stories, suggest pruning the weakest ones (lowest reuse count, narrowest applicability).

---

## Output Format

```
INTERVIEW PREP: {Company} — {Role}
Score: {from evaluation, if available}

PROCESS INTEL
[Format, rounds, timeline, tips — from Reddit or "no data available"]

STORIES (mapped to JD requirements)

1. [Story Title]
   Maps to: [requirement]
   Use when asked: [typical question]
   [STAR+R content]

2. [Story Title]
   ...

GENERAL TIPS
- [1-3 company-specific tips based on research and culture signals]
```
