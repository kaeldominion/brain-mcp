---
type: system
status: canonical
---

# Ingestion Protocol

Instructions for the admin agent: build or enrich this brain automatically from the owner's connected tools (email, calendar, task manager, drive, meeting notes), instead of asking the owner to dictate everything. Run during onboarding (after Phase 1) or any time the owner asks ("scan my workspace").

## Step 1 — Connector inventory

List the connectors you actually have access to (Google Workspace / Outlook, ClickUp or similar, Drive/OneDrive, Granola or similar, others). Report to the owner what you can reach and what you can't: "I have your calendar and ClickUp; I don't have email access — want to add it, or proceed without?" Never assume a connector exists; never nag about more than once.

## Step 2 — Offer the three modes

1. **Quick scan** (default, ~5 minutes): the last 30 days, conservative thresholds. Target 40–60 notes.
2. **Full scan**: 6–12 months of history, org-wide. Only on an explicit yes after you state what it will read and roughly how many notes it may create.
3. **Manual only**: skip ingestion entirely; the interview covers everything. A first-class choice — some owners don't want tools swept on day one. Respect it without comment.

## Step 3 — What to extract (quick-scan thresholds)

| Source | Extract | Threshold |
| --- | --- | --- |
| Email | People notes (name, role guess, relationship context) | corresponded ≥5 times in 30 days |
| Calendar | Meeting notes (title, date, attendees) + People for recurring attendees | meetings with ≥2 attendees; skip declined/private events |
| Tasks (ClickUp etc.) | Project notes + Open Actions | lists/projects touched in the last 30 days |
| Drive/storage | The truth-sources map in [[Company 2nd Brain Home]] | top 2 folder levels only — structure, never contents |
| Meeting recorder | Meeting notes with recording links; Decisions if explicit | last 30 days |

Full scan widens windows and drops thresholds moderately — it never relaxes the privacy rules below.

## Privacy rules (hard — no owner instruction overrides these)

1. **Structure and summaries only. Never content bodies.** A person note may say "supplier, weekly correspondence about villa maintenance" — never quote or paraphrase individual emails or messages.
2. **Skip anything personal**: personal calendars, events marked private, 1:1s that look non-work, personal folders. When unsure whether something is company or personal, leave it out and note the gap in the digest.
3. **Never ingest secrets** — credentials, banking details, HR/salary/medical content. If a source is full of such material (e.g. an HR folder), record only that it exists in the truth-sources map.
4. **Ambiguity goes to your inbox**, not to canonical folders — the owner places it during review.
5. Everything you create is `status: unverified` with provenance in the note body: source system and date range (e.g. "derived from calendar, Jun–Jul 2026").

## Step 4 — Filing rules

Use the templates; register every entity in [[Entity Index]]; check for existing notes before creating (the interview may already have covered an entity — enrich, don't duplicate); wikilink people ↔ companies ↔ projects ↔ meetings as you go.

## Step 5 — The digest (always)

End with a summary the owner can react to in one message:

> Scanned calendar + ClickUp (30 days). Created 23 people, 8 projects, 14 meetings, 6 open actions — all unverified. Skipped 112 low-signal contacts and 2 sources that looked personal. I couldn't reach email. Anything here that shouldn't be in the company brain?

Then hand over to the review flow: the onboarding Phase 6 review or the weekly ritual confirms and promotes. Never promote ingested notes yourself without the owner's confirmation.

## Session log

<!-- Append one line per ingestion run: date, mode, sources, notes created/skipped. -->
