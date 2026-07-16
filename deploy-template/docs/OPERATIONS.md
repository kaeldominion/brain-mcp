# Operations

Day-to-day running of a Company 2nd Brain install.

## The ./brain tool

All routine operations go through the TUI (or the underlying scripts headlessly):

| Command | Does | Script underneath |
| --- | --- | --- |
| `./brain setup` | Full first-install wizard | `scripts/bootstrap.sh` |
| `./brain add-agent` | Add an agent + token | `scripts/add-agent.sh` |
| `./brain rotate <name>` | Rotate one agent's token | `scripts/rotate-token.sh` |
| `./brain revoke <name>` | Remove an agent | `scripts/revoke-agent.sh` |
| `./brain status` | Stack + vault dashboard | `scripts/healthcheck.sh` |
| `./brain verify` | Acceptance suite vs live stack | `scripts/verify.sh` |

## Upgrades

1. Edit the pinned `ghcr.io/kaeldominion/brain-mcp:<tag>` in `docker-compose.yml`.
2. `source scripts/lib/compose.sh && compose pull && compose up -d` (the helper applies the right Traefik overlay for `TRAEFIK_MODE`).
3. `./brain verify`.

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
