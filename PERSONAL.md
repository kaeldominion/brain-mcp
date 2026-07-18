# Running a 2nd Brain for yourself

There is one product. A "personal" brain is not a different edition — it's the same server, vault, roles, audit, console and backups, deployed for a scope of **everything you run** instead of one organization. Two independent choices define any install:

## Choice 1 — exposure (the only thing setup asks)

| Where agents connect from | What you get |
| --- | --- |
| **Anywhere** | Public HTTPS behind Traefik on a server — for agents on other machines and always-on access |
| **My private network** | Localhost bind + Tailscale in front: reachable from all *your* devices with TLS, invisible to the public internet |
| **Only this machine** | Localhost only — a laptop-contained brain |

Pick by topology, not by whose brain it is. If your agents are Docker containers, Claude runs on another machine, or you want it always-on — a personal brain deserves a server install ("anywhere" or tailnet on a VPS) exactly like a company's.

## Choice 2 — scope (the onboarding interview asks, not the installer)

Phase 1 of the interview asks what should live in the brain:

- **One business** — even solo. A one-person company's brain is the *business's* brain with a headcount of one; when a team arrives you add agents with roles — same brain, no migration.
- **Everything you run** — the owner-centric brain: your ventures, personal brand, properties, the lot, each as first-class entities. The joins *between* your ventures are the value — and only your own brain may contain them.

The graduation rule that keeps this clean: **the moment a venture needs other people's agents sharing memory, it gets its own brain** — yours keeps your private view of it, plus links.

## Connecting your agents (every mode)

Each client gets its own token via `./brain add-agent` (instant, no restarts). The onboarding block prints the right URL for your mode, plus a ready-made Claude command:

```bash
claude mcp add --transport http company_brain <your-brain-url>/mcp \
  --header "Authorization: Bearer <token>"
```

Claude Desktop takes the same URL + header as a remote MCP connector.

**Agent in a Docker container on the same machine** (e.g. a dockerized Hermes): don't route through localhost or the public URL — attach it to the brain's network and use the internal address:

```bash
docker network connect brain-proxy <your-agent-container>
# then inside the agent:  http://brain-mcp:8000/mcp
```

(`brain-proxy` is the default network name — see `TRAEFIK_NETWORK` in `.env`.)

## Tailnet exposure in practice

Choose "my private network" in setup: it detects Tailscale, records your machine's MagicDNS name, and prints the one command:

```bash
tailscale serve --bg https / http://127.0.0.1:8000
```

Agents on any of your tailnet devices then use `https://<your-machine>.<tailnet>.ts.net/mcp`. Tokens stay mandatory — the tailnet is an outer wall, never the lock.

## Migrating an existing personal vault

Your notes are Markdown: drop them into the data directory (default `~/2nd-brain-data`), then let the onboarding interview + ingestion formalize them — Entity Index, wikilinks, frontmatter. Moving between exposures later is copying the data directory and re-running setup: same files, same config shape.
