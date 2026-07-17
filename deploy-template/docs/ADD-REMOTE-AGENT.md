# Adding an agent

Every agent — same VPS or across the world — is an external MCP client on `https://brain-mcp.<COMPANY_DOMAIN>/mcp`. There is no local/remote distinction: same-VPS traffic loops locally with ms-level overhead, irrelevant next to model latency. (Attaching an agent container to the Traefik Docker network is a purely optional local optimization; it changes nothing about auth.)

## Steps

1. On the VPS: `./brain add-agent` (or headless: `scripts/add-agent.sh finance --role editor`).
2. It prints **one copyable block**: the MCP connection config (URL + bearer token, shown once) plus the `company-brain` skill text. Paste the whole block into the agent's deployment config — that is the entire integration.
3. Restart the agent so tools are rediscovered; ask it to call `health_check`.

Give agents their own role with the minimum globs they need (edit `roles:` in `brain.config.yaml`) — don't reuse a broader role for convenience. Exactly one client may hold the `admin` role.

## Recommended hardening: Tailscale

Public HTTPS + hashed tokens + rate limits + default-deny ACLs is the supported default. A private overlay removes the public surface entirely:

1. Install Tailscale on the VPS and on each agent host; join the same tailnet.
2. Restrict Traefik to the tailnet: IP allowlist middleware for `100.64.0.0/10` (bundled mode: add it in `traefik/dynamic/security.yml`), or bind the entrypoint to the Tailscale interface.
3. Point agents at the tailnet name instead of the public domain.

Tokens stay mandatory either way — the network layer is an addition, never a replacement. Do not rely on obscurity or an unguessable URL.
