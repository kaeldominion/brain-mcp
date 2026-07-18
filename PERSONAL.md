# Personal 2nd Brain — the same product, on your own machine

A personal brain is **not a different thing**: it's the same server, vault, permissions, and console, installed in *local mode* — bound to `127.0.0.1`, no reverse proxy, no domains, no certificates. Every MCP client on your machine connects to it with its own token: your Hermes agent, Claude Code, Claude Desktop, anything that speaks MCP.

## Setup (needs Docker Desktop, python3, openssl)

```bash
git clone https://github.com/kaeldominion/brain-mcp
cp -r brain-mcp/deploy-template 2nd-brain
cd 2nd-brain
./brain setup        # choose "personal brain — on this machine"
```

The wizard skips everything server-ish (Traefik, domains, ACME) and gives you:

- MCP endpoint at `http://127.0.0.1:8000/mcp` (localhost only)
- your admin token, shown once
- optional web console at `http://127.0.0.1:3300` (`./brain console`)
- optional offsite backup to a private repo you own (`./brain backup`)

## Connecting your agents

Each client gets its **own** token via `./brain add-agent` (instant, no restarts):

**Hermes** — paste the printed `mcp_servers:` block into its config.

**Claude Code** — one command (printed in the onboarding block too):

```bash
claude mcp add --transport http company_brain http://127.0.0.1:8000/mcp \
  --header "Authorization: Bearer <token>"
```

**Claude Desktop** — add the same URL + Authorization header as a remote MCP server in its connector settings.

Roles apply exactly as on a company brain — you'll probably run everything as one or two clients, but nothing stops you giving a scratch agent contributor-only access.

## Migrating an existing personal vault

Your notes are just Markdown: drop them into the data directory you chose during setup (default `~/2nd-brain-data`), keep or adapt the folder taxonomy, and ask your agent to sweep them into shape (Entity Index, wikilinks, frontmatter) — or run the onboarding interview and let ingestion do the heavy lifting.

## Personal vs company — the only real differences

| | Personal (local mode) | Company (server) |
| --- | --- | --- |
| Where | your machine, `127.0.0.1` only | a VPS behind Traefik + HTTPS |
| Who connects | your own agents/tools | any agent anywhere, per-token |
| Setup asks | data directory | domain, DNS, certificates |
| Everything else | **identical** — vault, roles, audit, console, backups, `./brain` | identical |

Upgrade path: it's the same files and the same config — move the vault to a server install and switch mode whenever a personal brain needs to become reachable from elsewhere.

*(If you truly want zero infrastructure — one agent, direct file access, no MCP — the vault template still works as plain local files with the same conventions. But you lose multi-client access, locking, and audit; local mode is the recommended personal setup.)*
