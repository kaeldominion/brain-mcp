# brain-mcp

*Company 2nd Brain, by [Sentient Labs](https://sentientlabs.io) — open source, Apache-2.0*

A Dockerized [FastMCP](https://gofastmcp.com) service that is the **sole controlled writer** to an Obsidian-compatible Markdown vault, letting any number of AI agents (Hermes, Claude, anything MCP-capable — all external clients over HTTPS) share company knowledge safely.

One generic image, zero client-specific content. Per-client installs are thin private `brain-deploy-<client>` repos instantiated from [`deploy-template/`](deploy-template/README.md), which ships the compose stack (Traefik-aware), the `./brain` terminal console, agent onboarding, and docs. Self-host freely; Sentient Labs sells the managed install, updates, weekly review ritual, and agent onboarding.

## What it enforces

- **Per-agent bearer tokens** — server stores sha256 hashes only, constant-time comparison, tokens identified in logs/audit by prefix only.
- **Glob-based role ACLs** — default-deny, `deny > write > read` precedence, `{client}` interpolation, exactly one admin client. Authorization happens in the server before any tool executes.
- **Vault-root jail** — rejects absolute paths, `..` traversal, escaping symlinks, dot-files (`.git`, `.obsidian`, `.env`), and non-text extensions.
- **Safe concurrent writes** — per-file locks, read-latest-before-write, temp-file + atomic rename, hash-conditional section updates that return a structured `CONFLICT` instead of overwriting.
- **Append-only audit** — every write (allowed or denied) becomes a JSONL event (UTC time, client, role, tool, path, before/after hash) in a directory the MCP tools can't reach; size-based rotation.
- **In-app rate limiting** per token (local agents bypass Traefik, so edge limits aren't enough).
- **No hard delete** — `archive_note` moves to `_Archive/`; `restore_note` brings it back.
- **Log redaction** — bearer headers and token-shaped strings never reach any log.

## Tools

`health_check` (unauthenticated), `search_notes`, `read_note`, `read_note_section`, `list_directory`, `list_recent_changes`, `create_note`, `append_to_note`, `update_note_section` (requires `expected_hash`), `add_inbox_item`, `move_note`, and admin-only `rename_note`, `archive_note`, `restore_note`, `set_note_status` (promote `unverified` → `canonical`).

A plain `GET /health` route serves Docker/Traefik health checks.

## Install — `./brain setup` (the TUI does everything)

On the server (needs Docker + Compose v2, python3, openssl):

```bash
git clone https://github.com/kaeldominion/brain-mcp
cp -r brain-mcp/deploy-template 2nd-brain
cd 2nd-brain
./brain setup
```

That's the whole install. The guided wizard runs preflight checks, detects an existing Traefik (Hostinger boxes ship one) or deploys the bundled one, asks for your domain/email, generates hashed agent tokens, seeds the vault (including `_System/` — agent instructions, note templates, entity index, and the onboarding interview protocol), starts the stack, and runs the acceptance suite.

Then onboard each AI agent with:

```bash
./brain add-agent
```

which prints **one copyable block** — MCP URL + bearer token (shown once) + the company-brain skill text. Paste it into the agent's config; that's the entire integration. Agents connect to `https://brain-mcp.<domain>/mcp` with `Authorization: Bearer <token>`.

Roles out of the box: **admin** (full access, promotes notes to canonical — exactly one), **editor** (read/write its scoped areas + own inbox), **contributor** (read approved areas, write only its own inbox). Add your own roles in `brain.config.yaml`. Then give the admin agent the **daily triage + weekly review cron prompts** from [`deploy-template/docs/OPERATIONS.md`](deploy-template/docs/OPERATIONS.md) — that's what sweeps the inboxes and unverified notes the other agents produce.

Day-2 admin: just run **`./brain`** — an interactive console with everything (status, agents, tokens, offsite backup to your own private repo, verify, one-command update). Full details in [`deploy-template/README.md`](deploy-template/README.md) and `deploy-template/docs/`.

**Web console** (optional): `./brain console` enables a browser control room at `console.<domain>` — dashboard, one-click review queue for unverified notes, agent management with instant token issue/rotate/revoke (no restarts, via the dynamic client registry), read-only vault browser, and the audit trail. Ships as its own image (`ghcr.io/kaeldominion/brain-console`), talks only to brain-mcp's API, off by default.

**Multiple brains on one server**: each brain is one folder — copy the template again, run `./brain setup` with a different prefix/domain, and it shares the existing reverse proxy while staying fully isolated (own containers, vault, tokens, backups). See [deploy-template/README.md](deploy-template/README.md#multiple-brains-on-one-server).

### Personal brains — no server needed

One human + one agent doesn't need tokens, locking, or Docker: a personal 2nd Brain is the same vault template as **local files** next to your agent, with the same templates, entity index, and onboarding interview. See [PERSONAL.md](PERSONAL.md) — including the zero-conversion upgrade path to a full server install when a second agent or machine ever needs it. Company plans typically pair one shared server brain with a local personal brain per person.

### Manual / headless install (no TUI)

Everything the TUI does is plain scripts: `cp .env.example .env`, edit it, then `scripts/bootstrap.sh` — or wire the image yourself from `examples/brain.config.example.yaml` + `examples/docker-compose.example.yml` (vault at `/vault`, audit at `/audit`, config read-only at `/config/brain.config.yaml`; token hashes are `sha256` of `<deploy>_<client>_$(openssl rand -hex 16)` in the `MCP_TOKEN_HASH_*` env vars; the vault template is baked into the image at `/opt/vault-template`).

The config is validated at boot; the server refuses to start on any error. Adding a client or role is a config change + restart — never a code change.

## Development

```bash
uv sync
uv run pytest          # 110 tests incl. end-to-end streamable HTTP
docker build -t brain-mcp .
```

Releases: tag `vX.Y.Z` → CI runs tests, builds the image, and pushes `ghcr.io/kaeldominion/brain-mcp:X.Y.Z`. VPSs only ever pull images; they never see source.

## Layout

```
src/brain_mcp/    server.py config.py auth.py permissions.py paths.py
                  locking.py notes.py search.py audit.py ratelimit.py errors.py
tests/            full acceptance suite (auth, authz, jail, concurrency, HTTP e2e)
vault-template/   default Obsidian taxonomy + _System (instructions, templates,
                  Entity Index, Onboarding Protocol)
examples/         config + compose examples
```
