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

## Weekly review ritual

Prompt (or schedule) the admin agent to sweep inboxes and `status: unverified` notes — promote / merge / archive, repair wikilinks, update the Entity Index. This is the anti-rot mechanism; don't skip it.

## Backups

The `backup` sidecar commits and pushes the vault every `BACKUP_INTERVAL_SECONDS` (default 15 min). Check the last commit with `./brain status`. Audit logs live in `AUDIT_DIR` (outside the vault) — include that directory in VPS snapshots.
