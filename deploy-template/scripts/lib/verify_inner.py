"""Scripted external MCP test client for acceptance checks.

Exercises the server exactly like an agent would — streamable HTTP with a
bearer token per role, plus invalid-token and no-token cases. Piped by
verify.sh via `docker compose exec -T brain-mcp python -` (the image carries
fastmcp, so no host Python deps are needed); the calls themselves go through
the full HTTP auth path.
Unauthenticated checks always run. Authed checks need plaintext tokens in
VERIFY_TOKEN_ADMIN / VERIFY_TOKEN_OPERATIONS / VERIFY_TOKEN_STAFF
(supplied by ./brain setup right after token generation, or pasted by the
operator); without them those checks are reported as skipped.

Prints one line per check: 'ok NAME', 'FAIL NAME detail', 'skip NAME'.
Exit code 1 if anything failed.
"""

import asyncio
import os
import sys
import urllib.request

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

URL = "http://127.0.0.1:8000/mcp"
RESULTS = []


def report(status, name, detail=""):
    RESULTS.append(status)
    print(f"{status} {name}" + (f"  ({detail})" if detail else ""), flush=True)


def client(token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return Client(StreamableHttpTransport(URL, headers=headers))


async def expect_error(coro, code, name):
    try:
        await coro
        report("FAIL", name, "call unexpectedly succeeded")
    except Exception as e:
        if code in str(e):
            report("ok", name)
        else:
            report("FAIL", name, f"wrong error: {e}")


async def main():
    # -- health, no auth --
    try:
        body = urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5).read()
        report("ok" if b"vault_mounted" in body else "FAIL", "health route")
    except Exception as e:
        report("FAIL", "health route", str(e))

    async with client(None) as c:
        tools = await c.list_tools()
        report("ok" if len(tools) >= 15 else "FAIL", "tool discovery", f"{len(tools)} tools")
        hc = (await c.call_tool("health_check", {})).data
        report("ok" if hc["vault_mounted"] else "FAIL", "health_check tool")
        await expect_error(
            c.call_tool("read_note", {"path": "_System/Company 2nd Brain Home.md"}),
            "UNAUTHORIZED", "no token rejected",
        )
    async with client("bogus_token_1234567890abcdef") as c:
        await expect_error(
            c.call_tool("read_note", {"path": "_System/Company 2nd Brain Home.md"}),
            "UNAUTHORIZED", "invalid token rejected",
        )

    mgmt = os.environ.get("VERIFY_TOKEN_ADMIN")
    ops = os.environ.get("VERIFY_TOKEN_EDITOR")
    staff = os.environ.get("VERIFY_TOKEN_CONTRIBUTOR")

    if mgmt:
        async with client(mgmt) as c:
            note = "_Verify/acceptance-test.md"
            try:
                created = (await c.call_tool(
                    "create_note",
                    {"path": note, "content": "# Acceptance\n\n## Check\n\nv1\n"},
                )).data
                report("ok", "admin create")
                upd = (await c.call_tool(
                    "update_note_section",
                    {"path": note, "heading": "Check", "content": "v2",
                     "expected_hash": created["hash"]},
                )).data
                report("ok", "hash-guarded section update")
                await expect_error(
                    c.call_tool("update_note_section",
                                {"path": note, "heading": "Check", "content": "v3",
                                 "expected_hash": created["hash"]}),
                    "CONFLICT", "stale hash conflicts",
                )
                await c.call_tool("archive_note", {"path": note})
                await c.call_tool("restore_note", {"path": note})
                report("ok", "archive + restore")
                await c.call_tool("archive_note", {"path": note})  # leave vault clean
            except Exception as e:
                report("FAIL", "admin flow", str(e))
            await expect_error(
                c.call_tool("read_note", {"path": "../etc/passwd.md"}),
                "INVALID_PATH", "traversal rejected",
            )
            await expect_error(
                c.call_tool("create_note", {"path": "_Audit/x.md", "content": "#"}),
                "FORBIDDEN", "admin denied audit area",
            )
    else:
        report("skip", "admin checks (no VERIFY_TOKEN_ADMIN)")

    if ops:
        async with client(ops) as c:
            await expect_error(
                c.call_tool("create_note", {"path": "60 Finance/x.md", "content": "#"}),
                "FORBIDDEN", "editor denied finance",
            )
            r = (await c.call_tool("list_directory", {"path": "50 Operations"})).data
            report("ok" if "entries" in r else "FAIL", "editor lists its scoped area")
    else:
        report("skip", "editor checks (no VERIFY_TOKEN_EDITOR)")

    if staff:
        # client name is the token's middle segment (deploy_client_random)
        parts = staff.split("_")
        name = parts[1] if len(parts) >= 3 else "contributor"
        async with client(staff) as c:
            inbox = (await c.call_tool(
                "add_inbox_item",
                {"agent_name": name, "title": "verify item", "content": "from verify.sh"},
            )).data
            report("ok" if inbox["path"].startswith(f"90 Staff Inbox/{name}/") else "FAIL",
                   "contributor inbox write")
            await expect_error(
                c.call_tool("create_note", {"path": "80 Decisions/x.md", "content": "#"}),
                "FORBIDDEN", "contributor denied canonical write",
            )
    else:
        report("skip", "contributor checks (no VERIFY_TOKEN_CONTRIBUTOR)")

    fails = RESULTS.count("FAIL")
    print(f"\n{RESULTS.count('ok')} ok, {fails} failed, {RESULTS.count('skip')} skipped")
    sys.exit(1 if fails else 0)


asyncio.run(main())
