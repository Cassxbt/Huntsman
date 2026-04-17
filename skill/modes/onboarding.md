# Mode: Onboarding

Triggered when `load_profile()` returns `config/profile.yml` or `cv.md` in the `missing` list.
This runs once per missing file. After completion the user never sees it again.

---

## Goal

Collect everything needed to write `config/profile.yml` and `cv.md` through conversation — not a form. One topic at a time. Move quickly. At the end, write both files using the MCP tools so nothing is lost between sessions.

---

## Part 1 — Profile Interview

Run this when `config/profile.yml` is missing.

**Opening line:**

> "Before I can help you properly, I need 2 minutes to set up your profile. It only happens once — after this every session picks up where you left off. What's your name?"

**Ask in order, one at a time:**

**Q1 — Name** — already answered from opening line.

**Q2 — Contact**
"What's your email, and your LinkedIn username? (e.g. linkedin.com/in/**yourname**)"

**Q3 — Target roles**
"What roles are you targeting? Give me the exact job titles you'd apply to — priority order if you have one."

**Q4 — Domains**
"What industry verticals do you work in? e.g. Web3, AI/ML, FinTech, SaaS, DevTools, Climate."

**Q5 — Archetype**
"How do you see yourself? Builder (ships products), Researcher (deep technical), Leader (manages teams), Specialist (narrow expert), or Generalist (breadth across stack)?"
Map to: `builder`, `researcher`, `leader`, `specialist`, `generalist`.

**Q6 — Tech stack**
"Walk me through your tech stack. What do you use daily and know cold? What can you work in but wouldn't call a strength? What have you touched but are still learning?"
Categorise as: `primary`, `secondary`, `familiar`.

**Q7 — Compensation**
"What's your compensation floor — below that you won't consider the role? And your preferred number? Currency?"

**Q8 — Hard deal-breakers**
"Any instant rejections? Things you will not do regardless of salary — no remote option, junior in title, unpaid equity only, requires relocation, etc."

**Q9 — Location**
"Where are you based? Open to relocating, or remote only? Any timezone constraints for async overlap?"

**Q10 — Hero metric**
"What's your single best proof point — the thing that makes you stand out? A metric, a shipped product, a prize, an open-source project with real usage. Be specific."

**Q11 — Exit story**
"One sentence: why are you looking right now?"

**Confirm before writing:**

> "Here's what I've got:
> - Name: [name]
> - Targeting: [roles]
> - Stack: [primary skills]
> - Floor: [comp min] [currency], preferred [comp preferred]
> - Hard nos: [list]
> - Standout: [hero metric]
>
> Anything wrong or missing before I save this?"

Wait for confirmation. Apply any corrections. Then call:

```
write_profile(yaml_content="""
name: "[name]"
email: "[email]"
linkedin_username: "[username]"

target_roles:
  - "[role 1]"
  - "[role 2]"

domains:
  - "[domain 1]"

archetype: "[archetype]"

tech_stack:
  primary:
    - "[skill]"
  secondary:
    - "[skill]"
  familiar:
    - "[skill]"

comp:
  minimum: [number]
  preferred: [number]
  currency: "[USD/GBP/EUR/etc]"

hard_nos:
  - "[deal-breaker]"

location:
  current: "[city, country]"
  willing_to_relocate: [true/false]
  remote_only: [true/false]
  timezone_range: "[e.g. UTC-5 to UTC+2]"

hero_metrics:
  - "[proof point]"

exit_story: "[one sentence]"

reddit_watchlist:
  - "cscareerquestions"
  - "ExperiencedDevs"
  - "recruitinghell"
""")
```

Confirm: > "Profile saved."

---

## Part 2 — CV Interview

Run this when `cv.md` is missing (regardless of whether Part 1 also ran).

**Opening:**

> "Now I need your CV. You can paste your existing resume and I'll format it, or if you don't have one ready, describe your experience and I'll build it with you. Which do you prefer?"

**If they paste:**

Take their raw text. Clean it into the Huntsman Markdown format (see structure below). Show it to the user. Ask: "Does this look right? I'll save it once you confirm."

**If they describe (no resume ready):**

Ask role by role, starting from the most recent:

- "What's your current or most recent job title, company, and roughly when you started and ended?"
- "What were the 2-3 most impactful things you built or shipped there? Give me metrics if you have them."
- "What was your tech stack at that role?"
- Repeat for each role (cap at 4 roles — older roles get a brief line, not bullets).

Then ask:
- "Any side projects, open-source work, or freelance you'd want on the CV?"
- "Highest level of education? (Degree, institution, year — or 'self-taught' if that's your story.)"

Draft the full cv.md from their answers. Show it to the user. Ask: "Does this look right? I'll save it once you confirm."

**CV Markdown format:**

```
[Full Name]
[email] | [github or portfolio URL] | [linkedin URL]

WORK EXPERIENCE
[Job Title] | [Company] | [Employment Type] | [Month Year – Month Year or Present]
- [Strong verb] + [what you built] + [quantified result]
- [Strong verb] + [what you built] + [quantified result]
- Tech: [comma-separated stack]

PROJECTS
[Project Name] | [URL if public]
- [What it does and why it matters — one line]
- Tech: [stack]

TECHNICAL SKILLS
[Category]: [comma-separated skills]
[Category]: [comma-separated skills]

EDUCATION
[Degree or equivalent] | [Institution] | [Year]
```

Rules:
- Reverse chronological. Most recent role first.
- No markdown formatting inside bullets (no bold, no backticks).
- No tables. No columns. Plain text only.
- Every experience bullet: strong verb + what + quantified result where possible.
- Strong verbs: Architected, Built, Deployed, Engineered, Implemented, Integrated, Shipped, Scaled, Reduced, Increased, Led, Designed.

**Once confirmed, call:**

```
write_cv(markdown_content="[full cv.md content]")
```

Confirm: > "CV saved."

---

## Transition

After both files are written, say:

> "All set. Let's get back to what you needed."

Then execute the user's original request without re-summarising the onboarding.
