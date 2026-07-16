# Company 2nd Brain — deploy template

*by Sentient Labs*

Generic, client-agnostic deployment for [brain-mcp](../README.md). The stack is exactly **brain-mcp + backup sidecar + vault volume**, plus Traefik *only if the host doesn't already run one*. AI agents (Hermes or anything MCP-capable) are **not** part of this stack — they're deployed independently, and every agent everywhere is an external MCP client on `https://brain-mcp.<domain>/mcp`.

Copy this directory into a **private** `brain-deploy-<client>` repo per install; nothing here contains client specifics.

## Quick start

```bash
cp -r deploy-template 2nd-brain && cd 2nd-brain
./brain setup        # preflight → traefik detection → details → tokens → seed → start → verify
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
./brain add-agent          # or: scripts/add-agent.sh finance --role operations
```

Prints **one copyable block** — MCP URL + bearer token (shown once) + the `company-brain` skill text from `skills/company-brain.md`. Pasting that block into the agent's deployment config is the entire integration. Same flow for agents on the same VPS or across the world; there is no local/remote distinction (same-VPS HTTPS loops locally — ms-level overhead vs seconds of model latency).

## What's here

| Path | Purpose |
| --- | --- |
| `docker-compose.yml` | brain-mcp (pinned tag, `expose`d only) + backup sidecar |
| `compose.bundled-traefik.yml` / `compose.external-traefik.yml` | the two Traefik modes |
| `brain.config.yaml` | clients + roles + limits — the only file that varies meaningfully per client |
| `traefik/dynamic/security.yml` | headers, per-IP rate limit, body cap, TLS floor (bundled mode) |
| `skills/company-brain.md` | the skill text every agent gets in its onboarding block |
| `scripts/` | `bootstrap` `add-agent` `generate-secrets` `rotate-token` `revoke-agent` `backup-vault` `restore-vault` `healthcheck` `verify` `update` |
| `./brain` | terminal console wrapping those scripts (setup / add-agent / rotate / revoke / status / verify / update) |
| `docs/` | OPERATIONS · SECURITY · RECOVERY · ADD-REMOTE-AGENT |

Day-2 operations live in `docs/OPERATIONS.md`.
