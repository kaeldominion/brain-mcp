---
type: system
status: canonical
---

# AI Agent Instructions

Behavioral rules for every agent connected to this vault. Read this note at the start of a session before writing anything.

## Core workflow

1. **Search before answering.** Search the Company 2nd Brain before answering company-specific factual questions.
2. **Read before writing.** Read the relevant canonical note before modifying it.
3. **Unverified goes to the inbox.** Put unverified or staff-submitted information into your own inbox folder instead of presenting it as confirmed fact.
4. **Use the MCP tools only.** Never attempt direct filesystem access for Company Brain changes.

## Content rules

1. **One note per entity, one entity per note.** Check [[Entity Index]] before creating; never create a spelling-variant duplicate. Add every new entity to the index.
2. **Wikilink everything** — people ↔ companies ↔ properties ↔ meetings ↔ decisions.
3. **Templates are mandatory** for new entity notes — see `_System/Templates/`. Keep the template's headings intact; they are the contract for section updates.
4. **Everything you write is `status: unverified`** until promoted. Only the admin-role agent (acting on a human instruction) promotes notes to `canonical`.
5. **Preserve source and date** on every fact — "per owner, 2026-07-16" beats a bare claim.
6. **Sparse and correct beats stuffed and wrong.** Don't pad notes; link out instead.
7. **Large files never enter the vault** — store in Drive/object storage and link.
8. **No secrets, ever.** No API keys, bot tokens, passwords, OAuth tokens, banking credentials, or personal private notes.
9. **Decisions get their own note** in `80 Decisions` — never buried inside a meeting note. The meeting note links to the decision note.

## Ongoing hygiene

- **Daily:** capture into inboxes as unverified.
- **Weekly review (admin agent):** sweep unverified notes and inboxes — promote, merge, or archive; repair broken wikilinks; update [[Entity Index]].
- **Monthly:** archive stale notes in `85 Open Actions`; confirm procedures still match reality.
