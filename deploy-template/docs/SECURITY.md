# Security model

## Layers

1. **Traefik edge** — TLS, HTTP→HTTPS redirect, and (in bundled mode) security headers, per-IP rate limit, 2 MiB body cap. Only 80/443 are published on the host. In external mode the host's existing Traefik provides this layer — verify its redirect/TLS settings (`./brain setup` warns about gaps).
2. **Server auth** — every MCP client (local or remote) sends `Authorization: Bearer <token>`. The server stores sha256 hashes only (constant-time compare, no early exit) and identifies tokens in logs/audit by prefix only. Authorization (glob ACLs, default-deny, exactly one admin) is enforced in the server before any tool executes — never only at the edge, never only in prompts.
3. **Vault jail** — absolute paths, `..`, escaping symlinks, dot-files and non-text extensions are rejected regardless of role.
4. **Audit** — every write, allowed or denied, is an append-only JSONL event in `AUDIT_DIR`, unreachable via MCP tools.

## Token lifecycle

- Create: `./brain add-agent` (or `scripts/add-agent.sh`) — token printed once, only hash stored.
- Rotate: `./brain rotate <name>` — other agents unaffected.
- Revoke: `./brain revoke <name>` — client block removed, server restarted.

## Rules

- `.env` is chmod 600, gitignored, never printed. Prefer Docker secrets when the platform allows.
- No plaintext token ever lands in a repo, image, log, or the vault.
- Agents are external MCP clients — this stack never holds their sessions, credentials, or memory. Only company knowledge is shared, via MCP.
- No container mounts `/var/run/docker.sock` except Traefik (read-only, provider API only).
- Never put API keys, bot tokens, passwords, banking details, or personal notes in the vault.
- Images are pinned by version; upgrades are deliberate tag bumps.
