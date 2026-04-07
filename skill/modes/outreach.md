# Mode: Outreach

Triggered when the user asks to reach out to a hiring manager, recruiter, or contact at a company.
Also triggered automatically as part of the full pipeline when a job scores >= 4.5.

Before executing, read `skill/_shared.md` for language constraints and banned word lists.
All generated text (messages, emails) must follow those rules.

---

## Step 1 — Find the Right Person

Use `search_linkedin_people(keywords, location)` to identify the hiring manager or recruiter.

Search strategies (try in order until a good match is found):
1. `"{role_title} hiring manager {company_name}"` — direct hiring authority
2. `"engineering manager {company_name}"` — likely reports-to for IC roles
3. `"recruiter {company_name}"` — internal recruiter
4. `"talent acquisition {company_name}"` — TA team
5. `"{department} lead {company_name}"` — department head

From the search results, identify the best person to contact. Prefer:
- Someone whose title suggests direct hiring authority over this role
- Internal over agency recruiters
- People who have posted recently (active on LinkedIn)

---

## Step 2 — Pull Their Profile

Call `get_linkedin_profile(linkedin_username, sections="experience,posts")` on the identified person.

Extract:
- Their current role and how long they've been there
- Any recent posts (topics, tone, interests)
- Shared connections or experiences with the user
- Their background (did they come up through engineering? Through recruiting?)

---

## Step 3 — Draft the Connection Message

LinkedIn connection messages have a 300-character hard limit. Every character counts.

Structure:
```
[Hook — reference something specific about them: a recent post, their background, a shared interest]
[Proof — one concrete achievement from the user's hero_metrics that's relevant to the role]
[CTA — one clear, low-commitment ask]
```

Rules:
- 300 characters max. Not 301. Count carefully.
- The hook must be specific to this person. "I saw your company is hiring" is generic and gets ignored. "Your post about scaling the payments team resonated" is specific.
- The proof point must be relevant to the role, not just impressive in general.
- The CTA must be low-friction: "Would love to share a quick note about my fit for the {role} opening" or "Happy to send a 2-minute overview of relevant work if helpful."
- No flattery. No "I'm passionate about." No em dashes.
- Tone: "I'm choosing you" not "please choose me."

---

## Step 4 — Draft Follow-Up Sequence

If the connection is accepted but no response:

**Follow-up 1 (3-5 days later):**
- Reference the original message briefly
- Add one new data point not in the original message
- Same CTA or slightly adjusted
- Keep under 200 characters

**Follow-up 2 (5-7 days after follow-up 1):**
- Final touch — brief, respectful
- "Wanted to make sure this didn't get lost" framing
- If still no response after this, stop. Do not send a third follow-up.

---

## Step 5 — Draft Cold Email (if email is available)

If `get_linkedin_profile` returned contact info with an email, or if the user provides one:

Email structure (75-150 words):
1. One sentence: who you are and why you're writing (reference the specific role)
2. One quantified achievement relevant to their team's work
3. One sentence connecting your experience to their specific challenge
4. Clear ask: 10-15 minute call, or permission to send a detailed brief
5. Sign-off with name and LinkedIn URL

Rules:
- Subject line: specific, not clickbait. "[Role Title] — [One proof point]" works.
- No attachments in cold outreach. Link to portfolio or GitHub instead.
- No em dashes. No AI-pattern language.

---

## Output Format

```
OUTREACH: {Company} — {Role}

TARGET
Name: [person's name]
Title: [their title]
LinkedIn: [profile URL]
Why them: [one sentence — why this person is the right contact]

CONNECTION MESSAGE (X/300 characters)
[message text]

FOLLOW-UP 1 (send after 3-5 days if no response)
[message text]

FOLLOW-UP 2 (send after 5-7 more days if no response)
[message text]

COLD EMAIL (if email available)
Subject: [subject line]
[email body]
```
