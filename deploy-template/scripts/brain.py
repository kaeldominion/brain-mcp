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


def detect_traefik():
    """Return (mode, network) — 'external' + its network if a Traefik is
    already running on this host (Hostinger default), else ('bundled', None)."""
    r = subprocess.run(
        ["docker", "ps", "--format", "{{.ID}}\t{{.Names}}\t{{.Image}}"],
        capture_output=True, text=True,
    )
    for line in r.stdout.splitlines():
        cid, cname, image = (line.split("\t") + ["", ""])[:3]
        if "traefik" in image.lower() or "traefik" in cname.lower():
            nets = subprocess.run(
                ["docker", "inspect", cid, "-f",
                 "{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}"],
                capture_output=True, text=True,
            ).stdout.split()
            nets = [n for n in nets if n not in ("bridge", "host", "none")]
            return "external", (nets[0] if nets else None), cname
    return "bundled", None, None


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

    mode, network, tname = detect_traefik()
    if mode == "external":
        say(f"  ✓ existing Traefik detected ('{tname}', network: {network or 'unknown'})", style="green")
        say(
            "    brain-mcp will attach to it and route via labels.\n"
            "    Check that TRAEFIK_ENTRYPOINT / TRAEFIK_CERTRESOLVER in .env match its\n"
            "    configuration, and that it redirects HTTP→HTTPS — gaps there weaken TLS.",
            style="yellow",
        )
        if network is None:
            network = ask("Docker network of the existing Traefik", "traefik")
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
            .replace("TRAEFIK_MODE=bundled", f"TRAEFIK_MODE={mode}")
        )
        if network:
            text = text.replace("TRAEFIK_NETWORK=brain-proxy", f"TRAEFIK_NETWORK={network}")
        env_file.write_text(text)
        env_file.chmod(0o600)
        say("  ✓ .env written (fill in BACKUP_REMOTE / BACKUP_SSH_KEY before relying on backups)")

    grule()
    say("Running bootstrap (seed vault, backup repo, secrets, start, verify)…")
    run(["scripts/bootstrap.sh"])
    grule()

    say("Default agents: management (admin), operations, staff. Onboarding blocks:")
    for name, _role, _env in clients():
        if confirm(f"Print the onboarding block for '{name}' now (rotates its token)?"):
            cmd_rotate_silent(name)

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
    role = args[1] if len(args) > 1 else choose("Role", ["operations", "staff", "admin"])
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


COMMANDS = {
    "setup": cmd_setup,
    "add-agent": cmd_add_agent,
    "rotate": cmd_rotate,
    "revoke": cmd_revoke,
    "status": cmd_status,
    "verify": cmd_verify,
    "update": cmd_update,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        wordmark()
        panel(
            "usage: ./brain <command>\n\n"
            "  setup       first-install wizard (traefik-aware)\n"
            "  add-agent   onboard an agent: URL + token + skill block\n"
            "  rotate      rotate an agent's token\n"
            "  revoke      remove an agent\n"
            "  status      stack + vault dashboard\n"
            "  verify      run the acceptance suite\n"
            "  update      pull the latest release + restart + verify",
            title="brain",
        )
        footer()
        sys.exit(0 if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help") else 1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
    footer()


if __name__ == "__main__":
    main()
