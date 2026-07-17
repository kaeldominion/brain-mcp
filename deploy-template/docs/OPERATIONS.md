# Operations

Day-to-day running of a Company 2nd Brain install.

## The ./brain console

Run `./brain` with no arguments for the interactive admin console — every operation in one arrow-key menu, nothing to memorize. Direct commands exist for scripting:

| Command | Does | Script underneath |
| --- | --- | --- |
| `./brain` | Interactive admin console | (menu over the below) |
| `./brain setup` | Full first-install wizard | `scripts/bootstrap.sh` |
| `./brain add-agent` | Add an agent + token | `scripts/add-agent.sh` |
| `./brain rotate <name>` | Rotate one agent's token | `scripts/rotate-token.sh` |
| `./brain revoke <name>` | Remove an agent | `scripts/revoke-agent.sh` |
| `./brain backup` | Configure offsite backup (guided) | writes `.env`, restarts sidecar |
| `./brain console` | Enable/disable the web console | overlay + console token |
| `./brain status` | Stack + vault dashboard | `scripts/healthcheck.sh` |
| `./brain verify` | Acceptance suite vs live stack | `scripts/verify.sh` |
| `./brain update` | Pull latest release + restart + verify | `scripts/update.sh` |

## Upgrades

```bash
./brain update
```

One command: fetches the latest deploy template from GitHub, refreshes scripts/docs/compose (never touching your `.env`, `brain.config.yaml`, venv, or vault), adopts the template's pinned server image, pulls it, restarts, and re-runs the acceptance suite.

Manual equivalent (or to pin a specific version): edit the `ghcr.io/kaeldominion/brain-mcp:<tag>` pin in `docker-compose.yml`, then `source scripts/lib/compose.sh && compose pull && compose up -d && ./brain verify`. Rollback = re-pin the previous tag the same way.

Rollback = re-pin the previous tag and repeat. Vault and config are mounts; upgrades never touch them.

## Human vault access (read-only)

Humans never get a writable mount. Clone the backup repo, open it in Obsidian, `git pull` to refresh:

```bash
git clone <BACKUP_REMOTE> my-company-brain
```

All writes go through agents → MCP.

## Admin agent rituals (set these up — the brain doesn't clean itself)

Editors and contributors write into their scoped areas and inboxes as `status: unverified`; the admin agent is the one that turns that stream into canonical knowledge. Nothing in this stack schedules agents, so give the **admin agent** two cron jobs (Hermes cron or equivalent) with prompts like:

**Daily — inbox triage (files, never promotes):**

> Check the company brain: list recent changes and every note in `90 Staff Inbox/*`. For each new item: merge it into the right canonical note (as unverified), or file it as a new templated entity note, or flag it for me if it's unclear or contradicts something canonical. Update the Entity Index. Don't promote anything to canonical.

**Weekly — the review (proposes, then executes on confirmation):**

> Sweep all `status: unverified` notes in the company brain. Propose which should be promoted to canonical, merged, or archived — one line of reasoning each. After my confirmation: promote via `set_note_status`, archive stale items in `85 Open Actions`, repair broken wikilinks, reconcile the Entity Index.

The split matters: daily filing keeps inboxes empty without any human involvement; promotion stays a human-confirmed act so `canonical` keeps meaning something. This weekly review is the anti-rot mechanism — don't skip it.

The same pattern covers ingestion (e.g. an agent's hourly cron: "list new Granola meetings since last sync, file each as a meeting note with the recording link, decisions into `80 Decisions`, all unverified").

## Backups

The `backup` sidecar commits and pushes the vault every `BACKUP_INTERVAL_SECONDS` (default 15 min). Check the last commit with `./brain status`. Audit logs live in `AUDIT_DIR` (outside the vault) — include that directory in VPS snapshots.
