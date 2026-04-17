# Mode: LinkedIn Profile Audit

Triggered when the user asks to audit or optimise their LinkedIn profile.

---

## Step 1 — Pull the Live Profile

```
get_linkedin_profile(linkedin_username, sections="experience,education,skills,contact_info,honors")
```

If the username was not provided, ask for it before proceeding.

---

## Step 2 — Audit Every Section

For each section below, state the current content (verbatim if short), identify the gap, assign a priority, and provide paste-ready replacement copy. Do not skip sections — an empty section is still a finding.

**HEADLINE (P0 if generic or empty)**
- 220-character limit. Use every character for keyword density.
- Pattern: `[Primary Role] | [Top Tech Keywords] | [Domain] | [Credibility Signal]`
- Must contain recruiter search keywords. Generic titles do not rank.

**ABOUT (P0 if empty)**
- Min 40 words for All-Star status (required for full recruiter search visibility).
- LinkedIn's ranking system classifies expertise from this section.
- Structure: 1 positioning sentence, 3-5 achievement bullets with numbers, tech stack sentence, open to [roles] (remote), contact email.
- No filler language. Numbers beat adjectives. No em dashes. No AI-pattern language.

**EXPERIENCE (P0 if empty or generic titles)**
- Every role needs a description.
- Bullets: [Strong Verb] + [What] + [Quantified Outcome]
- Strong verbs: Architected, Built, Deployed, Engineered, Implemented, Integrated, Shipped, Scaled
- Freelance/contract counts — label it.
- No em dashes. No passive voice.

**SKILLS (P1)**
- 5+ skills materially increases recruiter search visibility — LinkedIn ranks fuller profiles higher.
- Top 3 pinned skills appear on the profile card. Pin highest-demand keywords.
- LinkedIn Recruiter has a "passed skill assessment" filter.
- Priority assessments: JavaScript, React.js, TypeScript, Python, Node.js, Git

**OPEN TO WORK (P1 if job-seeking)**
- Signals active availability to recruiters — use Recruiters Only to avoid alerting a current employer.
- Location: always "Remote" when targeting international roles.
- List specific job titles matching recruiter search terms.

**EDUCATION (P1 if empty)**
- Required for All-Star status.

**FEATURED (P1)**
- First item gets ~80% of clicks. Order by strategic priority.
- 4-6 items max. Best performers: GitHub, live project demo, prize certificate.

**PROFILE URL (P2)**
Change from default ID-number URL to linkedin.com/in/yourname.

**VERIFICATION BADGE (P2)**
Adds a trust signal — LinkedIn surfaces verified profiles more consistently in search.

**CONNECTIONS (P2)**
- Below 500 = smaller 2nd-degree pool.
- Build order: recruiters in your domain first, then developers at target companies.

**ACTIVITY (P2)**
- LinkedIn's algorithm classifies expertise from posts — posting off-niche suppresses reach in your target domain.
- Native documents and carousels consistently outperform external link posts in organic reach.
- Post 2-4x per week; never more than once per 24 hours. Mid-week mornings perform best.
- Put external links in the first comment, not the post body — LinkedIn deprioritizes posts that push users off-platform.
- Feed weight: Saves (highest) > Dwell time > See more > Comments > Shares > Likes (lowest)

---

## Step 3 — Output Format

```
## LinkedIn Audit: @[username]
Pulled: [date]

### CRITICAL (P0)
[list — fix these first or the profile will not rank]

### SECTION REPORT
[each section: Current → Issue → Fix with paste-ready copy]

### ALL-STAR CHECKLIST
- [ ] Photo  - [ ] Banner  - [ ] Headline  - [ ] About  - [ ] Experience  - [ ] Skills  - [ ] Education

### ESTIMATED IMPACT
[Which specific fixes unlock the most recruiter visibility and why]
```

---

## Recruiter Boolean Search Reference

Example patterns recruiters use in LinkedIn Recruiter — adapt to the user's target roles:

```
("[primary skill]" OR "[related skill]") AND ("developer" OR "engineer") NOT junior
("[domain]" OR "[related domain]") AND ("[framework]" OR "[language]")
("[specialty]" OR "[alternate term]") AND ("engineer" OR "developer")
```

---

## LinkedIn Profile SEO Reference

| Section | Search Weight |
|---|---|
| Headline | Highest |
| Current job title | Very high |
| Skills section | High |
| About section | High |
| Experience descriptions | Medium-high |
| Education | Medium |
