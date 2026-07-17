---
type: system
status: canonical
---

# Access and Contribution Rules

Human-readable summary of who can do what. The authoritative enforcement is the MCP server's role configuration (`brain.config.yaml`) — this note describes it; changing this note changes nothing.

## Roles

| Role | Read | Write |
| --- | --- | --- |
| admin | Entire vault | Entire vault except audit internals and this note; only role that promotes notes to canonical |
| editor | Its scoped areas (e.g. properties, operations, meetings, people, projects) + system notes | Its scoped areas and its own inbox |
| contributor | Approved procedures and reference notes + system notes | Only its own inbox folder |

Installs may define additional roles (finance, director, …) in the server configuration; this table describes the defaults.

## Ground rules

- The MCP server is the sole writer to this vault. Humans read via the read-only Git clone.
- Nothing is hard-deleted; archived notes move to `_Archive`.
- Every write is audited (who, what, when, before/after hash) outside the vault.
- Agents cannot modify audit history, `.obsidian` workspace state, or this note.
