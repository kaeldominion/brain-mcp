# brain-mcp

The Company 2nd Brain MCP server: a Dockerized [FastMCP](https://gofastmcp.com) service that is the **sole controlled writer** to an Obsidian-compatible Markdown vault, letting multiple isolated AI agents (local and remote) share company knowledge safely.

One generic image, zero client-specific content. Per-client installs are thin `brain-deploy-<client>` repos: compose file + `brain.config.yaml` + seeded vault.

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

## Install

```bash
docker pull ghcr.io/kaeldominion/brain-mcp:0.1.0
```

1. Copy `examples/brain.config.example.yaml` → your `brain.config.yaml`; define clients and roles.
2. Generate a token per client: `token=<deploy>_<client>_$(openssl rand -hex 16)`; give the plaintext to the agent, put `echo -n "$token" | shasum -a 256` into the matching `MCP_TOKEN_HASH_*` env var.
3. Seed the vault from `vault-template/` (baked into the image at `/opt/vault-template`). Include `_System/` — it carries the agent instructions, templates, entity index, and the onboarding interview protocol.
4. Run per `examples/docker-compose.example.yml` (vault mounted at `/vault`, audit dir at `/audit`, config read-only at `/config/brain.config.yaml`).

Agents connect to `http://brain-mcp:8000/mcp` (or `https://brain-mcp.<domain>/mcp` through a reverse proxy) with header `Authorization: Bearer <token>`.

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
