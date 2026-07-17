#!/usr/bin/env python3
"""Small helper for brain.config.yaml edits that must preserve comments.

Used by add-agent.sh / rotate-token.sh / the ./brain TUI. Text-based insert
and remove so hand-written comments survive; YAML is re-parsed afterwards to
guarantee the result is still valid.
"""

import argparse
import re
import sys
from pathlib import Path

CLIENT_BLOCK = "  - name: {name}\n    token_hash_env: {env}\n    role: {role}\n"


def _yaml():
    try:
        import yaml
    except ImportError:
        sys.exit("error: pyyaml is required — run scripts/bootstrap.sh (or ./brain setup) first")
    return yaml


def load(path: Path) -> dict:
    data = _yaml().safe_load(path.read_text())
    if not isinstance(data, dict):
        sys.exit(f"error: {path} is not a valid config")
    return data


def env_var_for(name: str) -> str:
    return "MCP_TOKEN_HASH_" + re.sub(r"[^A-Za-z0-9]", "_", name).upper()


def has_client(path: Path, name: str) -> bool:
    return any(c.get("name") == name for c in load(path).get("clients", []))


def cmd_has_client(args):
    sys.exit(0 if has_client(args.config, args.name) else 1)


def cmd_list_clients(args):
    for c in load(args.config).get("clients", []):
        print(f"{c.get('name')}\t{c.get('role')}\t{c.get('token_hash_env')}")


def cmd_env_var(args):
    print(env_var_for(args.name))


def cmd_add_client(args):
    data = load(args.config)
    if has_client(args.config, args.name):
        sys.exit(f"error: client {args.name!r} already exists")
    # 'console' is a built-in system role (admin-equivalent, for the web console)
    if args.role not in data.get("roles", {}) and args.role != "console":
        sys.exit(f"error: unknown role {args.role!r} (defined: {', '.join(data.get('roles', {}))})")
    admins = [c for c in data.get("clients", []) if c.get("role") == "admin"]
    if args.role == "admin" and admins:
        sys.exit(f"error: an admin client already exists ({admins[0].get('name')!r}); exactly one admin is allowed")

    text = args.config.read_text()
    block = CLIENT_BLOCK.format(name=args.name, env=env_var_for(args.name), role=args.role)
    lines = text.splitlines(keepends=True)
    # insert after the last "  - name:" client entry (before the roles: key)
    last_client_end = None
    in_clients = False
    for i, line in enumerate(lines):
        if re.match(r"^clients:\s*$", line):
            in_clients = True
            last_client_end = i + 1
        elif in_clients and re.match(r"^\S", line):
            break
        elif in_clients:
            last_client_end = i + 1
    if last_client_end is None:
        sys.exit("error: no 'clients:' section found")
    lines.insert(last_client_end, block)
    new_text = "".join(lines)
    _yaml().safe_load(new_text)  # must still parse
    args.config.write_text(new_text)
    print(f"added client {args.name!r} with role {args.role!r} ({env_var_for(args.name)})")


def cmd_remove_client(args):
    if not has_client(args.config, args.name):
        sys.exit(f"error: client {args.name!r} not found")
    data = load(args.config)
    target = next(c for c in data["clients"] if c.get("name") == args.name)
    if target.get("role") == "admin":
        sys.exit("error: refusing to remove the admin client")

    lines = args.config.read_text().splitlines(keepends=True)
    out, skipping = [], False
    for line in lines:
        if re.match(rf"^  - name: {re.escape(args.name)}\s*$", line):
            skipping = True
            continue
        if skipping and (re.match(r"^  - name:", line) or re.match(r"^\S", line)):
            skipping = False
        if not skipping:
            out.append(line)
    new_text = "".join(out)
    parsed = _yaml().safe_load(new_text)
    assert all(c.get("name") != args.name for c in parsed.get("clients", []))
    args.config.write_text(new_text)
    print(f"removed client {args.name!r}")


# ---- dynamic registry (clients.yaml) ---------------------------------------
# The server hot-reloads this file: mutations here need NO restart, and the
# resulting agents are manageable from the web console.


def _load_dynamic(path: Path) -> list:
    if not path.exists():
        return []
    data = _yaml().safe_load(path.read_text()) or {}
    return list(data.get("clients", []))


def _write_dynamic(path: Path, entries: list) -> None:
    import os
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".clients-", suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        f.write("# Managed by brain-mcp tooling. Hashes only — never tokens.\n")
        _yaml().safe_dump({"clients": entries}, f, sort_keys=False)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def _all_names(args) -> set:
    static = {c.get("name") for c in load(args.config).get("clients", [])}
    return static | {c.get("name") for c in _load_dynamic(args.clients_file)}


def _new_token(deploy: str, name: str) -> str:
    import secrets

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "client"
    return f"{deploy}_{slug}_{secrets.token_hex(16)}"


def _sha256(token: str) -> str:
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()


def cmd_is_dynamic(args):
    sys.exit(0 if any(c.get("name") == args.name for c in _load_dynamic(args.clients_file)) else 1)


def cmd_add_dynamic(args):
    data = load(args.config)
    if args.role not in data.get("roles", {}) and args.role != "console":
        sys.exit(f"error: unknown role {args.role!r} (defined: {', '.join(data.get('roles', {}))})")
    if args.name in _all_names(args):
        sys.exit(f"error: client {args.name!r} already exists")
    if args.role == "admin":
        sys.exit("error: the admin client is env-managed; exactly one admin is allowed")
    token = _new_token(args.deploy, args.name)
    entries = _load_dynamic(args.clients_file)
    entries.append({"name": args.name, "role": args.role, "token_hash": _sha256(token)})
    _write_dynamic(args.clients_file, entries)
    print(token)


def cmd_rotate_dynamic(args):
    entries = _load_dynamic(args.clients_file)
    target = next((c for c in entries if c.get("name") == args.name), None)
    if target is None:
        sys.exit(f"error: client {args.name!r} not found in {args.clients_file}")
    token = _new_token(args.deploy, args.name)
    target["token_hash"] = _sha256(token)
    _write_dynamic(args.clients_file, entries)
    print(token)


def cmd_remove_dynamic(args):
    entries = _load_dynamic(args.clients_file)
    if not any(c.get("name") == args.name for c in entries):
        sys.exit(f"error: client {args.name!r} not found in {args.clients_file}")
    _write_dynamic(args.clients_file, [c for c in entries if c.get("name") != args.name])
    print(f"removed client {args.name!r}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("brain.config.yaml"))
    parser.add_argument("--clients-file", type=Path, default=None)
    parser.add_argument("--deploy", default="brain")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("has-client")
    p.add_argument("name")
    p.set_defaults(fn=cmd_has_client)

    p = sub.add_parser("list-clients")
    p.set_defaults(fn=cmd_list_clients)

    p = sub.add_parser("env-var")
    p.add_argument("name")
    p.set_defaults(fn=cmd_env_var)

    p = sub.add_parser("add-client")
    p.add_argument("name")
    p.add_argument("--role", required=True)
    p.set_defaults(fn=cmd_add_client)

    p = sub.add_parser("remove-client")
    p.add_argument("name")
    p.set_defaults(fn=cmd_remove_client)

    for cmd_name, fn in [
        ("is-dynamic", cmd_is_dynamic),
        ("rotate-dynamic", cmd_rotate_dynamic),
        ("remove-dynamic", cmd_remove_dynamic),
    ]:
        p = sub.add_parser(cmd_name)
        p.add_argument("name")
        p.set_defaults(fn=fn)

    p = sub.add_parser("add-dynamic")
    p.add_argument("name")
    p.add_argument("--role", required=True)
    p.set_defaults(fn=cmd_add_dynamic)

    args = parser.parse_args()
    if args.cmd in ("is-dynamic", "add-dynamic", "rotate-dynamic", "remove-dynamic") and not args.clients_file:
        sys.exit("error: --clients-file is required for dynamic commands")
    args.fn(args)


if __name__ == "__main__":
    main()
