# Security model

## Layers

1. **Traefik edge** — TLS, HTTP→HTTPS redirect, and (in bundled mode) security headers, per-IP rate limit, 2 MiB body cap. Only 80/443 are published on the host. In external mode the host's existing Traefik provides this layer — verify its redirect/TLS settings (`./brain setup` warns about gaps).
2. **Server auth** — every MCP client (local or remote) sends `Authorization: Bearer <token>`. The server stores sha256 hashes only (constant-time compare, no early exit) and identifies tokens in logs/audit by prefix only. Authorization (glob ACLs, default-deny, exactly one admin) is enforced in the server before any tool executes — never only at the edge, never only in prompts.
3. **Vault jail** — absolute paths, `..`, escaping symlinks, dot-files and non-text extensions are rejected regardless of role.
4. **Audit** — every write, allowed or denied, is an append-only JSONL event in `AUDIT_DIR`, unreachable via MCP tools.

## Web console

The console (`2ndbrain.<domain>`, optional, off by default) is a new public surface — treat it accordingly:

- It authenticates with a dedicated `console`-role token via session login (httpOnly cookie, 12h). That token has admin-equivalent vault access — guard it like the admin token.
- The console container never mounts the vault; every action goes through brain-mcp's API, so server-side ACL/audit still applies to everything it does.
- **Defence-in-depth is on you**: the login is the only gate by default. For anything beyond a trial, add an IP allowlist (bundled mode: Traefik middleware in `traefik/dynamic/security.yml`) or put `2ndbrain.<domain>` behind Tailscale. Disable when unused: `./brain console`.

## Token lifecycle

- Create: `./brain add-agent`, the web console, or `scripts/add-agent.sh` — token shown once, only its hash stored, live immediately (dynamic registry, no restart).
- Rotate: `./brain rotate <name>` or the console — instant for dynamic agents; other agents unaffected.
- Revoke: `./brain revoke <name>` or the console — the token stops authenticating immediately; the agent's notes and audit history remain.
- The bootstrap admin (and any pre-registry clients) are env-managed: rotating those goes through `./brain` and restarts the server.

## Rules

- `.env` is chmod 600, gitignored, never printed. Prefer Docker secrets when the platform allows.
- No plaintext token ever lands in a repo, image, log, or the vault.
- Agents are external MCP clients — this stack never holds their sessions, credentials, or memory. Only company knowledge is shared, via MCP.
- `brain-mcp` and `backup` never mount `/var/run/docker.sock`. The only socket mount in the project is the **optional bundled-Traefik overlay** (read-only, required by Traefik's Docker provider for label discovery); external-traefik mode avoids any socket mount in this stack entirely.
- Never put API keys, bot tokens, passwords, banking details, or personal notes in the vault.
- Images are pinned by version; upgrades are deliberate tag bumps.
