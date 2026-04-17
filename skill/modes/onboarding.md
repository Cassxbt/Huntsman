# Mode: Onboarding

Triggered when `load_profile()` returns `config/profile.yml` in the `missing` list.
This runs once. After completion the user never sees it again.

---

## Goal

Collect everything needed to write a complete `config/profile.yml` and, if absent, a baseline `cv.md`. Do this conversationally — not as a form. One topic at a time. Move quickly.

---

## Opening Line

Say exactly this, then wait:

> "Before I can help you properly, I need 2 minutes to set up your profile. It only happens once — after this every session picks up where you left off. What's your name?"

---

## Interview Questions (ask in order, one at a time)

**Q1 — Name**
"What's your name?" (or already answered from the opening)

**Q2 — Contact**
"What's your email, and what's your LinkedIn username? (e.g. linkedin.com/in/**yourname**)"

**Q3 — Target roles**
"What roles are you targeting? Give me the exact job titles you'd apply to — priority order if you have one."

**Q4 — Domains**
"What industry verticals do you work in? For example: Web3, AI/ML, FinTech, SaaS, DevTools, Climate."

**Q5 — Archetype**
"How do you see yourself? Builder (ships products), Researcher (deep technical), Leader (manages teams), Specialist (narrow expert), or Generalist (breadth across stack)?"
Map the answer to one of: `builder`, `researcher`, `leader`, `specialist`, `generalist`.

**Q6 — Tech stack**
"Walk me through your tech stack. What do you use daily and know cold? What can you work in but wouldn't call a strength? What have you touched but are still learning?"
Categorise as: `primary`, `secondary`, `familiar`.

**Q7 — Compensation**
"What's your compensation floor — below that you won't consider the role? And what's your preferred number? Currency?"

**Q8 — Hard deal-breakers**
"Any instant rejections? Things you will not do regardless of salary — no remote option, junior in title, unpaid equity only, requires relocation, etc."

**Q9 — Location**
"Where are you based? Are you open to relocating, or remote only? Any timezone constraints for async overlap?"

**Q10 — Hero metric**
"What's your single best proof point — the thing that makes you stand out on a CV? A metric, a shipped product, a prize, an open-source project with real usage. Be specific."

**Q11 — Exit story**
"One sentence: why are you looking right now?"

---

## Confirm Before Writing

After collecting all answers, play them back in a short summary:

> "Here's what I've got:
> - Name: [name]
> - Targeting: [roles]
> - Stack: [primary skills]
> - Floor: [comp min] [currency], preferred [comp preferred]
> - Hard nos: [list]
> - Standout: [hero metric]
>
> Anything wrong or missing before I save this?"

Wait for confirmation or corrections. Apply corrections. Then proceed.

---

## Write the Profile

Assemble the YAML using the exact structure from `config/profile.example.yml` and call:

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

Confirm to the user:

> "Profile saved. You won't be asked this again."

---

## Handle Missing CV

If `cv.md` was also in the `missing` list from `load_profile()`:

> "One more thing — I don't have your CV yet. You can either paste your current resume text, or describe your experience and I'll draft a structured `cv.md` for you. Which do you prefer?"

- **If they paste:** Format it into clean Markdown following the resume structure in `_shared.md`. Save as `cv.md` in the project root by asking the user to run: `cat > cv.md` and paste the output. (Direct file writes are not supported — `write_profile` is the only write tool for setup files.)
- **If they describe:** Ask follow-up questions role by role. Draft `cv.md`. Show it. Ask them to save it.

---

## Transition

After profile (and optionally CV) are written, say:

> "All set. Let's get back to what you needed."

Then execute the user's original request without re-summarising the onboarding.
