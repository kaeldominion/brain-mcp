#!/usr/bin/env python3
"""./brain — guided terminal console for a Company 2nd Brain install.

Thin wrapper: every action shells out to the scripts in scripts/ (one code
path; the scripts stay headless-usable for CI and automation). Degrades to
plain prompts when rich/questionary or a smart terminal are unavailable.
"""

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    console = Console()
    RICH = console.is_terminal
except ImportError:  # pre-bootstrap or dumb terminal: plain text
    console = None
    RICH = False

# Sentient Labs signature gradient (teal → cyan → violet → purple).
# Identity only — success/warn/error stay conventional green/amber/red.
# Rich downgrades truecolor to 256-color automatically; RICH=False → plain text.
GRADIENT = ((0x2D, 0xD4, 0xBF), (0x22, 0xD3, 0xEE), (0xA7, 0x8B, 0xFA), (0xC0, 0x84, 0xFC))
TEAL = "#2DD4BF"
VIOLET = "#A78BFA"


def gradient_text(s, bold=False):
    """Left-to-right character-level ramp across the Sentient gradient."""
    if not RICH:
        return s
    text = Text()
    span = max(len(s) - 1, 1)
    for i, ch in enumerate(s):
        pos = (i / span) * (len(GRADIENT) - 1)
        j = min(int(pos), len(GRADIENT) - 2)
        f = pos - j
        r, g, b = (round(GRADIENT[j][k] + (GRADIENT[j + 1][k] - GRADIENT[j][k]) * f) for k in range(3))
        style = f"rgb({r},{g},{b})"
        text.append(ch, style=f"bold {style}" if bold else style)
    return text


def grule(width=None):
    """Section divider: a gradient-ramped horizontal rule."""
    w = width or (console.width if RICH else 72)
    line = "─" * max(int(w), 10)
    if RICH:
        console.print(gradient_text(line))
    else:
        print(line)


def wordmark():
    grule()
    if RICH:
        console.print(gradient_text("███  2ND BRAIN MCP  ███", bold=True))
        console.print("company memory for AI agents", style="dim")
        console.print("— by Sentient Labs · sentientlabs.co", style="dim")
    else:
        print("███  2ND BRAIN MCP  ███")
        print("company memory for AI agents")
        print("— by Sentient Labs · sentientlabs.co")
    grule()


def footer():
    if RICH:
        console.print("2nd Brain MCP · by Sentient Labs", style="dim")
    else:
        print("2nd Brain MCP · by Sentient Labs")

try:
    import questionary

    INTERACTIVE = sys.stdin.isatty()
except ImportError:
    questionary = None
    INTERACTIVE = sys.stdin.isatty()


def say(text, style=""):
    if RICH:
        console.print(text, style=style)
    else:
        print(re.sub(r"\[/?[a-z ]+\]", "", str(text)))


def panel(text, title="", border=None):
    if RICH:
        console.print(Panel(text, title=f"[bold white]{title}[/bold white]" if title else None,
                            border_style=border or "cyan"))
    else:
        print(f"\n=== {title} ===\n{text}\n")


def ask(prompt, default=None):
    if questionary and INTERACTIVE:
        return questionary.text(prompt, default=default or "").ask()
    raw = input(f"{prompt} [{default or ''}]: ").strip()
    return raw or default


def choose(prompt, choices):
    if questionary and INTERACTIVE:
        return questionary.select(prompt, choices=choices).ask()
    print(prompt)
    for i, c in enumerate(choices, 1):
        print(f"  {i}) {c}")
    while True:
        pick = input("> ").strip()
        if pick.isdigit() and 1 <= int(pick) <= len(choices):
            return choices[int(pick) - 1]


def confirm(prompt):
    if questionary and INTERACTIVE:
        return questionary.confirm(prompt, default=False).ask()
    return input(f"{prompt} [y/N]: ").strip().lower() == "y"


def run(cmd, capture=False, env=None, check=True):
    """Run a script; stream output unless capture=True."""
    full_env = {**os.environ, **(env or {})}
    if capture:
        r = subprocess.run(cmd, capture_output=True, text=True, env=full_env)
        if check and r.returncode != 0:
            say(r.stdout + r.stderr, style="red")
            sys.exit(r.returncode)
        return r
    r = subprocess.run(cmd, env=full_env)
    if check and r.returncode != 0:
        sys.exit(r.returncode)
    return r


def show_block_once(name, block):
    """Display an agent onboarding block (URL + token + skill) exactly once —
    the one moment of drama: gradient-framed reveal."""
    grule()
    panel(
        block + "\n\nPaste this into the agent's deployment config now. "
        "Shown once.",
        title=f"onboarding block: {name}",
        border=VIOLET,
    )
    grule()
    if INTERACTIVE:
        input("Press Enter to clear it from the screen... ")
        if RICH:
            console.clear()
        else:
            print("\033[2J\033[H", end="")


DEDICATED_NET = "2nd-brain-proxy"


def detect_traefik():
    """Inspect any running Traefik (Hostinger ships one) and pull everything
    the deploy needs from its actual container config: attachable network,
    the entrypoint bound to :443, and its certresolver name. Returns a dict
    with mode 'external' + details, or mode 'bundled' if no Traefik runs."""
    import json

    r = subprocess.run(
        ["docker", "ps", "--format", "{{.ID}}\t{{.Names}}\t{{.Image}}"],
        capture_output=True, text=True,
    )
    for line in r.stdout.splitlines():
        cid, cname, image = (line.split("\t") + ["", ""])[:3]
        if "traefik" not in image.lower() and "traefik" not in cname.lower():
            continue
        raw = subprocess.run(["docker", "inspect", cid], capture_output=True, text=True).stdout
        try:
            info = json.loads(raw)[0]
        except (ValueError, IndexError):
            return {"mode": "external", "id": cid, "name": cname, "network": None,
                    "entrypoint": None, "resolver": None}
        all_nets = info.get("NetworkSettings", {}).get("Networks", {})
        nets = [n for n in all_nets if n not in ("bridge", "host", "none")]
        host_mode = "host" in all_nets or info.get("HostConfig", {}).get("NetworkMode") == "host"
        argv = " ".join((info.get("Args") or []) + (info.get("Config", {}).get("Cmd") or []))
        m = re.search(r"--entry[pP]oints?\.([\w-]+)\.address=:?443\b", argv)
        entrypoint = m.group(1) if m else None
        m = re.search(r"--certificates[rR]esolvers?\.([\w-]+)\.", argv)
        resolver = m.group(1) if m else None
        return {"mode": "external", "id": cid, "name": cname,
                "network": nets[0] if nets else None, "host_mode": host_mode,
                "entrypoint": entrypoint, "resolver": resolver}
    return {"mode": "bundled"}


def attach_network_to_traefik(traefik_id):
    """Traefik had no attachable network (host networking / default bridge):
    create a dedicated one and connect Traefik to it — no guessing, no prompt."""
    subprocess.run(["docker", "network", "create", DEDICATED_NET],
                   capture_output=True, text=True)  # exists already → fine
    subprocess.run(["docker", "network", "connect", DEDICATED_NET, traefik_id],
                   capture_output=True, text=True)  # already connected → fine
    check = subprocess.run(
        ["docker", "network", "inspect", DEDICATED_NET, "-f",
         "{{range .Containers}}{{.Name}} {{end}}"],
        capture_output=True, text=True,
    )
    return DEDICATED_NET if check.returncode == 0 and check.stdout.strip() else None


def ensure_venv():
    """The scripts prefer .venv/bin/python; make sure it exists early."""
    if not (ROOT / ".venv" / "bin" / "python").exists():
        say("Creating tooling venv (.venv)…")
        run([sys.executable, "-m", "venv", ".venv"])
        run([".venv/bin/pip", "install", "-q", "--upgrade", "pip", "pyyaml", "rich", "questionary"])


def clients():
    py = str(ROOT / ".venv" / "bin" / "python")
    if not Path(py).exists():
        py = sys.executable
    r = run([py, "scripts/lib/config_edit.py", "list-clients"], capture=True)
    return [line.split("\t") for line in r.stdout.strip().splitlines() if line]


# ---- commands --------------------------------------------------------------


def cmd_setup(_):
    wordmark()
    panel(
        "This wizard installs the Company 2nd Brain:\n"
        "preflight → traefik detection → company details → tokens → vault seed → start → verify.\n\n"
        "AI agents are NOT part of this stack — onboard each one afterwards with\n"
        "./brain add-agent (prints a copyable URL + token + skill block).",
        title="setup",
    )
    checks = [
        ("Docker", ["docker", "--version"]),
        ("Docker Compose v2", ["docker", "compose", "version"]),
        ("python3", ["python3", "--version"]),
        ("openssl", ["openssl", "version"]),
    ]
    ok = True
    for label, cmd in checks:
        good = subprocess.run(cmd, capture_output=True).returncode == 0
        say(("  ✓ " if good else "  ✗ ") + label, style="green" if good else "red")
        ok &= good
    if not ok:
        say("Fix the ✗ items and re-run.", style="red")
        sys.exit(1)
    ensure_venv()

    det = detect_traefik()
    mode = det["mode"]
    network = entrypoint = resolver = None
    if mode == "external":
        say(f"  ✓ existing Traefik detected ('{det['name']}') — brain-mcp will attach to it", style="green")
        network = det["network"]
        if network:
            say(f"  ✓ Traefik network: {network}", style="green")
        elif det.get("host_mode"):
            # host-networked Traefik reaches container IPs directly; it can't
            # (and doesn't need to) join another network — just give brain-mcp one
            subprocess.run(["docker", "network", "create", DEDICATED_NET],
                           capture_output=True, text=True)
            network = DEDICATED_NET
            say(f"  ✓ Traefik uses host networking — brain-mcp gets its own '{DEDICATED_NET}' network, reachable directly", style="green")
        else:
            say(f"  ▲ Traefik has no attachable network — creating '{DEDICATED_NET}' and connecting Traefik to it", style="yellow")
            network = attach_network_to_traefik(det["id"])
            if network:
                say(f"  ✓ Traefik connected to '{network}'", style="green")
            else:
                say("  ✗ could not connect Traefik to a network automatically", style="red")
                network = ask("Docker network to share with Traefik", DEDICATED_NET)
        entrypoint = det["entrypoint"]
        resolver = det["resolver"]
        say(
            f"  {'✓' if entrypoint else '▲'} HTTPS entrypoint: "
            + (entrypoint or "not detectable (file-based config?) — using 'websecure'; fix TRAEFIK_ENTRYPOINT in .env if different"),
            style="green" if entrypoint else "yellow",
        )
        say(
            f"  {'✓' if resolver else '▲'} certificate resolver: "
            + (resolver or "not detectable — using 'letsencrypt'; fix TRAEFIK_CERTRESOLVER in .env if different"),
            style="green" if resolver else "yellow",
        )
        say("    Also confirm the existing Traefik redirects HTTP→HTTPS — gaps there weaken TLS.", style="dim")
    else:
        say("  ✓ no existing Traefik — the bundled one will be deployed on 80/443", style="green")

    env_file = ROOT / ".env"
    if not env_file.exists():
        (ROOT / ".env.example").exists() or sys.exit("missing .env.example")
        text = (ROOT / ".env.example").read_text()
        prefix = ask("Deploy prefix (short, e.g. acme)", "brain")
        domain = ask("Company domain (for brain-mcp.<domain>)", "example.com")
        email = ask("ACME email for TLS certificates", f"admin@{domain}")
        vault = ask("Vault directory on this host", f"/srv/{prefix}-2nd-brain")
        text = (
            text.replace("DEPLOY_PREFIX=brain", f"DEPLOY_PREFIX={prefix}")
            .replace("COMPANY_DOMAIN=example.com", f"COMPANY_DOMAIN={domain}")
            .replace("ACME_EMAIL=admin@example.com", f"ACME_EMAIL={email}")
            .replace("VAULT_DIR=/srv/company-2nd-brain", f"VAULT_DIR={vault}")
            .replace("AUDIT_DIR=/srv/company-2nd-brain-audit", f"AUDIT_DIR={vault}-audit")
            .replace("CLIENTS_DIR=/srv/company-2nd-brain-clients", f"CLIENTS_DIR={vault}-clients")
            .replace("TRAEFIK_MODE=bundled", f"TRAEFIK_MODE={mode}")
        )
        if network:
            text = text.replace("TRAEFIK_NETWORK=brain-proxy", f"TRAEFIK_NETWORK={network}")
        if entrypoint:
            text = text.replace("TRAEFIK_ENTRYPOINT=websecure", f"TRAEFIK_ENTRYPOINT={entrypoint}")
        if resolver:
            text = text.replace("TRAEFIK_CERTRESOLVER=letsencrypt", f"TRAEFIK_CERTRESOLVER={resolver}")
        env_file.write_text(text)
        env_file.chmod(0o600)
        say("  ✓ .env written (fill in BACKUP_REMOTE / BACKUP_SSH_KEY before relying on backups)")

    grule()
    say("Running bootstrap (seed vault, backup repo, secrets, start, verify)…")
    run(["scripts/bootstrap.sh"])
    grule()

    if not backup_configured():
        say("Offsite backup protects the brain if this server dies — strongly recommended.")
        if confirm("Configure offsite backup now? (you can do it later: ./brain backup)"):
            cmd_backup([])

    admin = next((c[0] for c in clients() if c[1] == "admin"), "admin")
    say(f"Your install has one agent: '{admin}' (the admin). Its onboarding block:")
    cmd_rotate_silent(admin)
    while confirm("Add another agent now? (you can always do this later with ./brain add-agent)"):
        cmd_add_agent([])

    domain = _env_value("COMPANY_DOMAIN")
    grule()
    if RICH:
        console.print(gradient_text("✓  INSTALL COMPLETE", bold=True))
    else:
        print("INSTALL COMPLETE")
    panel(
        "Endpoint for every agent (local or remote — all external MCP clients):\n"
        f"  https://brain-mcp.{domain}/mcp\n\n"
        "Onboard agents any time with: ./brain add-agent\n"
        "Next: connect the admin agent and say hello — it will offer to run the\n"
        "onboarding interview (_System/Onboarding Protocol.md).",
        title="install complete",
        border=TEAL,
    )
    grule()


def cmd_rotate_silent(name):
    """Rotate + print the full onboarding block for an existing agent."""
    r = run(["scripts/rotate-token.sh", name], capture=True)
    m = re.search(r"new token: (\S+)", r.stdout)
    if m:
        show_block_once(name, onboarding_block(name, m.group(1)))


def onboarding_block(name, token):
    domain = _env_value("COMPANY_DOMAIN")
    skill = (ROOT / "skills" / "company-brain.md").read_text()
    skill_text = skill.split("---", 2)[-1].strip() if "---" in skill else skill.strip()
    return (
        "# MCP connection (this token is shown ONCE; only its hash is stored)\n"
        "mcp_servers:\n"
        "  company_brain:\n"
        f'    url: "https://brain-mcp.{domain}/mcp"\n'
        "    headers:\n"
        f'      Authorization: "Bearer {token}"\n'
        "    timeout: 120\n"
        "    connect_timeout: 30\n\n"
        f"{skill_text}"
    )


def _env_value(key):
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    return ""


def cmd_add_agent(args):
    name = args[0] if args else ask("Agent name")
    role = args[1] if len(args) > 1 else choose(
        "Role",
        ["editor — read/write its scoped areas + own inbox",
         "contributor — read approved areas, write own inbox only",
         "custom (define it in brain.config.yaml first)"],
    )
    role = role.split(" ")[0]
    if role.startswith("custom"):
        say("Add the role under roles: in brain.config.yaml, then re-run ./brain add-agent.", style="yellow")
        return
    r = run(["scripts/add-agent.sh", name, "--role", role], capture=True)
    m = re.search(r"Bearer (\S+)", r.stdout)
    if m:
        show_block_once(name, onboarding_block(name, m.group(1).rstrip('"')))
    else:
        say(r.stdout)


def cmd_rotate(args):
    name = args[0] if args else choose("Rotate which agent?", [c[0] for c in clients()])
    if not confirm(f"Rotate the token for '{name}'? The old token stops working immediately."):
        return
    cmd_rotate_silent(name)


def cmd_revoke(args):
    name = args[0] if args else choose("Revoke which agent?", [c[0] for c in clients()])
    if not confirm(f"Revoke '{name}'? Its token stops authenticating immediately."):
        return
    run(["scripts/revoke-agent.sh", name])


def cmd_status(_):
    run(["scripts/healthcheck.sh"], check=False)
    vault = _env_value("VAULT_DIR")
    if vault and Path(vault).is_dir():
        notes = list(Path(vault).rglob("*.md"))
        unverified = sum(1 for n in notes if "status: unverified" in n.read_text(errors="replace"))
        if RICH:
            t = Table(title="vault")
            t.add_column("notes")
            t.add_column("unverified")
            t.add_row(str(len(notes)), str(unverified))
            console.print(t)
        else:
            print(f"vault: {len(notes)} notes, {unverified} unverified")
    say("\nagents:", style="bold")
    for name, role, _env in clients():
        say(f"  {name}  ({role})")


def cmd_verify(_):
    run(["scripts/verify.sh"], check=False)


def cmd_update(args):
    run(["scripts/update.sh", *args[:1]])


def cmd_console(_):
    enabled = _env_value("CONSOLE_ENABLED") == "true"
    domain = _env_value("COMPANY_DOMAIN")
    if enabled:
        say(f"Web console is ENABLED at https://console.{domain}", style="green")
        if confirm("Disable it?"):
            set_env("CONSOLE_ENABLED", "false")
            run(["bash", "-c",
                 "source scripts/lib/compose.sh && docker compose -f docker-compose.yml "
                 "-f compose.console.yml stop console 2>/dev/null; compose up -d --remove-orphans"])
            say("console disabled.")
        return

    panel(
        "The web console is the browser control room: dashboard, review queue,\n"
        "agents, vault browser, audit trail — at https://console." + (domain or "<domain>") + "\n\n"
        "Login uses a dedicated console token (created now, shown once).\n"
        "It is protected by that login; for defence-in-depth add an IP\n"
        "allowlist or Tailscale — see docs/SECURITY.md.",
        title="web console",
    )
    if not confirm("Enable the web console?"):
        return
    py = str(ROOT / ".venv" / "bin" / "python")
    if not Path(py).exists():
        py = sys.executable
    r = subprocess.run([py, "scripts/lib/config_edit.py", "has-client", "console-web"])
    if r.returncode != 0:
        run([py, "scripts/lib/config_edit.py", "add-client", "console-web", "--role", "console"])
    token = run(["scripts/generate-secrets.sh", "console-web", "--quiet-token-only"],
                capture=True).stdout.strip()
    set_env("CONSOLE_ENABLED", "true")
    compose_cmd("up", "-d")
    say(f"  ✓ console starting at https://console.{domain} (DNS: point console.{domain} at this server)", style="green")
    show_block_once("console-web", f"Console login token:\n\n  {token}\n\nUse it on the sign-in screen.")


def set_env(key, value):
    env_file = ROOT / ".env"
    lines = env_file.read_text().splitlines() if env_file.exists() else []
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    env_file.write_text("\n".join(lines) + "\n")
    env_file.chmod(0o600)


def compose_cmd(*args, check=True):
    return run(["bash", "-c", 'source scripts/lib/compose.sh && compose "$@"', "--", *args],
               check=check)


def backup_configured():
    remote = _env_value("BACKUP_REMOTE")
    return remote and "YOUR_ORG" not in remote


def cmd_backup(_):
    panel(
        "Offsite backup pushes the vault (every ~15 min) to a private Git repo\n"
        "that YOU own — your data never goes anywhere else.\n\n"
        "Before continuing: create an empty PRIVATE repo\n"
        "(GitHub → New repository → Private → no README).",
        title="backup settings",
    )
    current = _env_value("BACKUP_REMOTE")
    if backup_configured():
        say(f"current remote: {current}")
    url = ask("SSH URL of your private backup repo",
              current if backup_configured() else "git@github.com:YOU/company-brain-backup.git")
    if not url or "YOUR_ORG" in url or url.startswith("git@github.com:YOU/"):
        say("No repo set — backup stays local-only (vault history on this server).", style="yellow")
        return

    keydir = ROOT / ".backup-key"
    key = keydir / "id_ed25519"
    if not key.exists():
        keydir.mkdir(mode=0o700, exist_ok=True)
        run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "2nd-brain-backup", "-f", str(key)])
        say("  ✓ deploy key generated", style="green")
    pub = (keydir / "id_ed25519.pub").read_text().strip()
    panel(pub, title="deploy key — add this to the backup repo", border=TEAL)
    say("GitHub: repo → Settings → Deploy keys → Add deploy key → paste → tick 'Allow write access'.")
    if INTERACTIVE:
        input("Press Enter once the key is added... ")

    set_env("BACKUP_REMOTE", url)
    set_env("BACKUP_SSH_KEY", str(key))
    compose_cmd("up", "-d", "backup")
    say("Testing a push…")
    r = compose_cmd("run", "--rm", "--entrypoint", "sh", "backup", "/backup/backup-vault.sh",
                    check=False)
    if r.returncode == 0:
        say("  ✓ backup pushed — offsite backup is live (check: ./brain status)", style="green")
    else:
        say("  ✗ push failed — check the repo URL and that the deploy key has write access, "
            "then run backup settings again.", style="red")


COMMANDS = {
    "setup": cmd_setup,
    "add-agent": cmd_add_agent,
    "rotate": cmd_rotate,
    "revoke": cmd_revoke,
    "status": cmd_status,
    "verify": cmd_verify,
    "update": cmd_update,
    "backup": cmd_backup,
    "console": cmd_console,
}

MENU = [
    ("status — stack, vault, agents, last backup", cmd_status),
    ("add agent — onboard a new agent (URL + token + skill)", cmd_add_agent),
    ("rotate token — new token for an agent", cmd_rotate),
    ("revoke agent — remove an agent", cmd_revoke),
    ("console — enable/disable the web console", cmd_console),
    ("backup settings — offsite backup to your private repo", cmd_backup),
    ("verify — run the acceptance suite", cmd_verify),
    ("update — pull the latest release + restart + verify", cmd_update),
    ("quit", None),
]


def menu():
    """No-args interactive admin console — nothing to memorize."""
    wordmark()
    if not (ROOT / ".env").exists():
        say("Not installed yet — starting setup.\n", style="yellow")
        cmd_setup([])
        return
    if not backup_configured():
        say("▲ offsite backup is NOT configured — pick 'backup settings' below.", style="yellow")
    while True:
        say("")
        label = choose("2nd Brain admin — pick an action", [m[0] for m in MENU])
        fn = dict(MENU).get(label)
        if fn is None or label is None:
            break
        try:
            fn([])
        except SystemExit:
            pass
        except KeyboardInterrupt:
            break


def usage():
    wordmark()
    panel(
        "./brain              interactive admin console (start here)\n"
        "./brain <command>    direct commands:\n\n"
        "  setup       first-install wizard (traefik-aware)\n"
        "  add-agent   onboard an agent: URL + token + skill block\n"
        "  rotate      rotate an agent's token\n"
        "  revoke      remove an agent\n"
        "  console     enable/disable the web console\n"
        "  backup      configure offsite backup (your own private repo)\n"
        "  status      stack + vault dashboard\n"
        "  verify      run the acceptance suite\n"
        "  update      pull the latest release + restart + verify",
        title="brain",
    )


def main():
    if len(sys.argv) < 2:
        if INTERACTIVE:
            menu()
        else:
            usage()
        footer()
        return
    if sys.argv[1] not in COMMANDS:
        usage()
        footer()
        sys.exit(0 if sys.argv[1] in ("-h", "--help") else 1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
    footer()


if __name__ == "__main__":
    main()
