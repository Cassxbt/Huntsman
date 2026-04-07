# Mode: Company Research

Triggered when the user asks to research a company, or automatically before any evaluation.
Combines LinkedIn company data with Reddit intelligence for a complete picture.

---

## Data Gathering

Run these in sequence:

1. **LinkedIn:** `get_linkedin_company(company_identifier)` — main page + about subpage.
2. **Reddit reviews:** `search_reddit("working at {company_name}", sort_by="top", time_filter="year", limit=10)` — employee and candidate perspectives.
3. **Reddit interviews:** `search_reddit("{company_name} interview", subreddit="cscareerquestions", sort_by="top", time_filter="year", limit=5)` — interview process reports.
4. **Reddit salary:** `search_reddit("{company_name} salary OR compensation OR TC", subreddit="cscareerquestions", sort_by="relevance", time_filter="year", limit=5)` — comp data points.

If any Reddit search returns a highly relevant post (score > 50, multiple comments), call `get_reddit_post(url_or_id, max_comments=20)` to get the full discussion.

If the company is small or niche (< 50 employees, no Reddit presence), skip Reddit and note "No Reddit data available — company may be too small for community coverage."

---

## Analysis Checklist

From the gathered data, evaluate:

**Legitimacy**
- Does the LinkedIn page have a real company description, employee count, and posting history?
- Is the website linked from LinkedIn a real, maintained site?
- Are there real employees visible on LinkedIn?
- Verdict: confirmed / unverified / suspicious

**Business context**
- What does the company actually do? (One sentence, plain English)
- What stage are they at? (Pre-seed, seed, Series A-D, public, bootstrapped)
- How many employees? (From LinkedIn data)
- What domain? Does it align with the user's target domains from profile.yml?

**Culture signals**
- What language does the company use to describe itself? (Echo these exact words in applications)
- What do they emphasize — engineering excellence, speed, user impact, innovation, mission?
- Reddit sentiment: what do employees and candidates say? Summarize the consensus, not outliers.
- Red flags from Reddit: toxic management mentions, layoff patterns, interview horror stories, broken promises on remote work.

**Compensation intelligence**
- Is comp stated in the JD?
- Reddit data points (any TC/salary figures mentioned, with context)
- Market estimate based on company stage + domain + role level

**Interview process**
- Number of rounds (if known from Reddit)
- What to expect (coding challenge? System design? Behavioral? Take-home?)
- Timeline from application to offer (if known)
- Known red flags (ghosting, excessive rounds, lowball offers)

---

## Output Format

```
COMPANY RESEARCH: {Company Name}

Legitimacy:    confirmed / unverified / suspicious
Stage:         [funding stage or "public" or "bootstrapped"]
Size:          [employee count from LinkedIn]
Domain:        [industry] — [alignment with user's target domains]
Remote:        [policy from JD or LinkedIn]

WHAT THEY DO
[2-3 sentences in plain English]

CULTURE SIGNALS
Language they use: [exact phrases from their LinkedIn — echo these in applications]
Emphasis: [what they value]
Reddit consensus: [summary of employee/candidate sentiment, or "no data"]

COMPENSATION
Stated: [range or "not stated"]
Reddit: [any data points found, or "no data"]
Estimate: [$X–$Y based on {reasoning}]

INTERVIEW PROCESS
Rounds: [number or "unknown"]
Format: [what to expect, or "unknown"]
Timeline: [application to offer, or "unknown"]
Watch out for: [known issues, or "nothing flagged"]

RED FLAGS
[list, or "none found"]

VERDICT: APPLY / PROCEED WITH CAUTION ({reason}) / SKIP ({reason})
```

---

## When Called Standalone

If the user asks to research a company without evaluating a specific job, produce the report above and stop. Do not generate a resume or run the evaluation pipeline.

If a specific role is mentioned alongside the company, suggest running the full evaluation mode after the research is complete.
