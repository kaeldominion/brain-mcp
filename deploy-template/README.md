# Company 2nd Brain — deploy template

*by Sentient Labs*

Generic, client-agnostic deployment for [brain-mcp](../README.md). The stack is exactly **brain-mcp + backup sidecar + vault volume**, plus Traefik *only if the host doesn't already run one*. AI agents (Hermes or anything MCP-capable) are **not** part of this stack — they're deployed independently, and every agent everywhere is an external MCP client on `https://brain-mcp.<domain>/mcp`.

Copy this directory into a **private** `brain-deploy-<client>` repo per install; nothing here contains client specifics.

## Quick start

```bash
curl -fsSL https://raw.githubusercontent.com/kaeldominion/brain-mcp/main/install.sh | bash
# → stamps this kit into ./2nd-brain and runs the guided setup
```

Headless: `cp .env.example .env`, edit it, then `scripts/bootstrap.sh`.

## Two Traefik modes (both first-class)

| Mode | When | What happens |
| --- | --- | --- |
| `external` | Host already runs Traefik (Hostinger VPSes ship one on 80/443) | brain-mcp attaches to that Traefik's Docker network and is routed via container labels. Set `TRAEFIK_NETWORK` / `TRAEFIK_ENTRYPOINT` / `TRAEFIK_CERTRESOLVER` in `.env` to match it. Never deploy a second Traefik. |
| `bundled` | No reverse proxy on the host (fresh DigitalOcean box) | `compose.bundled-traefik.yml` deploys our hardened Traefik: TLS via Let's Encrypt, HTTP→HTTPS redirect, security headers, per-IP rate limit, body cap. |

`./brain setup` detects which applies and writes `TRAEFIK_MODE` to `.env`; every script honors it via `scripts/lib/compose.sh`. Run `./brain verify` after switching modes — the acceptance suite checks the active mode.

## Onboarding an agent

```bash
./brain add-agent          # or: scripts/add-agent.sh finance --role editor
```

Prints **one copyable block** — MCP URL + bearer token (shown once) + the `company-brain` skill text from `skills/company-brain.md`. Pasting that block into the agent's deployment config is the entire integration. Agents are live the moment they're created (dynamic registry — no restarts), and equally manageable from the web console. Same flow for agents on the same VPS or across the world; there is no local/remote distinction (same-VPS HTTPS loops locally — ms-level overhead vs seconds of model latency).

## The web console (optional)

```bash
./brain console        # enable → prints the login token once
```

Browser control room at `https://2ndbrain.<domain>`: dashboard (note counts, unverified queue, agents, backup state, activity feed), the **review queue** (promote / archive unverified notes and inbox items with one click — the weekly ritual becomes a 10-minute session), agent management (add/rotate/revoke, token shown once), read-only vault browser with search, and the filterable audit trail. It talks only to brain-mcp's API — never the vault filesystem. Off by default; read `docs/SECURITY.md` before exposing it.

## What's here

| Path | Purpose |
| --- | --- |
| `docker-compose.yml` | brain-mcp (pinned tag, `expose`d only) + backup sidecar |
| `compose.bundled-traefik.yml` / `compose.external-traefik.yml` | the two Traefik modes |
| `compose.console.yml` | the web console overlay (`CONSOLE_ENABLED` / `./brain console`) |
| `brain.config.yaml` | clients + roles + limits — the only file that varies meaningfully per client |
| `traefik/dynamic/security.yml` | headers, per-IP rate limit, body cap, TLS floor (bundled mode) |
| `skills/company-brain.md` | the skill text every agent gets in its onboarding block |
| `scripts/` | `bootstrap` `add-agent` `generate-secrets` `rotate-token` `revoke-agent` `backup-vault` `restore-vault` `healthcheck` `verify` `update` |
| `./brain` | interactive admin console (run with no args — arrow-key menu for everything); direct subcommands: setup / add-agent / rotate / revoke / console / backup / status / verify / update |
| `docs/` | OPERATIONS · SECURITY · RECOVERY · ADD-REMOTE-AGENT |

## Multiple brains on one server

Each brain is one folder with its own containers, vault, tokens, and backup repo — fully isolated. They share only the reverse proxy (one Traefik owns 80/443; every brain registers its own hostname under its own deploy prefix):

```bash
cp -r ~/brain-mcp/deploy-template ~/2nd-brain-companyx
cd ~/2nd-brain-companyx && ./brain setup     # different prefix + domain + backup repo
```

Run as many as the box can hold (~100MB RAM each). Manage each from its own folder: `cd <folder> && ./brain`.

Day-2 operations live in `docs/OPERATIONS.md`.
