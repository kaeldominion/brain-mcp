# Recovery

## A note was damaged or wrongly changed

```bash
scripts/restore-vault.sh "50 Operations/Procedures/Pool Cleaning.md"          # last good commit
scripts/restore-vault.sh "50 Operations/Procedures/Pool Cleaning.md" <sha>    # specific commit
```

The restore touches the working tree only; the next backup cycle commits it. (Archived notes don't need Git: `restore_note` via the admin agent brings them back from `_Archive/`.)

## The whole vault is gone (disk loss, bad migration)

1. Provision the host, install Docker, clone this deploy repo, restore `.env` from your secrets store.
2. `scripts/restore-vault.sh --full /srv/<client>-2nd-brain`
3. Point `VAULT_DIR` at it and `docker compose up -d`.
4. `./brain verify`.

Tokens survive in `.env` (hashes) + agent configs (plaintext), so agents reconnect unchanged. If `.env` is lost too, rotate every agent (`./brain rotate`).

## The VPS is gone entirely

Same as above on a fresh box, plus restore `AUDIT_DIR` from the latest VPS snapshot if audit history matters. DNS: repoint `brain-mcp.<domain>` at the new IP; Traefik reissues certificates automatically.

## Test this quarterly

Run the full-restore drill into a scratch directory and diff against the live vault:

```bash
scripts/restore-vault.sh --full /tmp/restore-drill && diff -r /tmp/restore-drill $VAULT_DIR --exclude=.git
```
