---
type: system
status: canonical
---

# Onboarding Protocol

Instructions for the admin/management agent on a fresh install: build this brain by interviewing the business owner (over Telegram/chat), creating notes through the MCP tools as answers arrive. The brain interviews its way into existence — no manual seeding.

## Interviewer rules

- One question at a time. Dig with follow-ups before moving to the next topic.
- Summarize back what you heard before writing it into the vault.
- Never invent facts to fill a template — leave sections empty rather than guess.
- Every note you create is `status: unverified` until Phase 6 confirmation.
- Use the templates in `_System/Templates/` and register every entity in [[Entity Index]].
- The protocol is phased so it can pause and resume across days. **End every session by appending one line to the Session log below**, always naming the highest phase reached, e.g. `- 2026-07-17 — Phase 3 reached, 14 notes created`. When the Phase 6 review is confirmed, append a final line containing the words `Onboarding complete`. (The console reads these lines to show progress.)
- Target: roughly 30–50 seed notes by the end of Phase 6.

## Phase 0 — Orientation

Explain to the owner what the brain is, what you will ask, and that everything starts unverified until they confirm it.

## Phase 1 — The business

What the company does, entities and legal structure, who owns what, key relationships. Output: Company notes in `10 Companies` + fill in [[Company 2nd Brain Home]].

## Phase 2 — Entity sweep

People (staff, clients, vendors, partners), assets (properties/products/whatever the business runs on), active projects. For each: name, role, contact context, current state. Output: one templated note each + [[Entity Index]] rows.

## Phase 3 — Truth sources

Where does knowledge live today (WhatsApp, sheets, email, people's heads)? What is authoritative vs gossip? Output: recorded in [[Company 2nd Brain Home]] under "Truth sources"; informs later ingestion.

## Phase 4 — Operations

The recurring processes: how things actually get done, step by step, exceptions included. Ask "what happens when X goes wrong?" follow-ups. Output: Procedure notes in `50 Operations/Procedures`.

## Phase 5 — Money and decisions

How money flows (summaries, never credentials), recent significant decisions and why. Output: notes in `60 Finance` + `80 Decisions`.

## Phase 6 — Review

Present the [[Entity Index]] and note count to the owner. Flag gaps ("you mentioned a plumber twice but I have no vendor note"). On the owner's confirmation, promote the confirmed core notes to `canonical`.

## Session log

<!-- Append one line per interview session: date, phase reached, notes created. -->
