# company-brain skill

Paste this into the agent's skills/instructions alongside its MCP config
(./brain add-agent prints it together with the URL and token).

---

You have access to your company's shared 2nd Brain — a knowledge vault — via
the `company_brain` MCP server.

1. At the start of a session, read `_System/AI Agent Instructions.md` from the
   vault and follow its rules for everything you write there.
2. Search the brain (`search_notes`) before answering any company-specific
   factual question; prefer what the vault says over memory.
3. Read the relevant note before modifying it, and use the returned hash when
   updating a section.
4. Unverified or secondhand information goes to your own inbox
   (`add_inbox_item`), never into canonical notes.
5. Never store secrets in the vault. Use the MCP tools only — never direct
   filesystem access.

**Admin agents only:** when the vault is empty or the owner asks, offer to run
the structured onboarding interview in `_System/Onboarding Protocol.md` —
one question at a time, creating notes as answers arrive.
