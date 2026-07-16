"""End-to-end tests over real streamable HTTP: uvicorn + FastMCP client."""

import logging
import os
import socket
import threading
import time

import pytest
import uvicorn
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.exceptions import ToolError

from tests.conftest import TOKEN_ENV, TOKENS, VALID_CONFIG

pytestmark = pytest.mark.integration


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start(app) -> tuple[uvicorn.Server, threading.Thread, int]:
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started:
        if time.time() > deadline:
            raise RuntimeError("uvicorn did not start")
        time.sleep(0.02)
    return server, thread, port


@pytest.fixture(scope="module")
def stack(tmp_path_factory):
    from brain_mcp.server import build_server

    base = tmp_path_factory.mktemp("integration")
    vault = base / "vault"
    for d in [
        "_System",
        "10 Companies",
        "50 Operations/Procedures",
        "60 Finance",
        "90 Staff Inbox/staff",
        "_Archive",
    ]:
        (vault / d).mkdir(parents=True)
    (vault / "50 Operations" / "Procedures" / "Cleaning.md").write_text(
        "# Cleaning\n\n## Steps\n\nMop daily.\n"
    )
    audit = base / "audit"
    audit.mkdir()
    cfg = base / "brain.config.yaml"
    cfg.write_text(VALID_CONFIG.format(vault_root=vault, audit_dir=audit))
    os.environ.update(TOKEN_ENV)

    mcp = build_server(cfg)
    server, thread, port = _start(mcp.http_app(path="/mcp"))
    yield {"url": f"http://127.0.0.1:{port}/mcp", "vault": vault, "audit": audit}
    server.should_exit = True
    thread.join(timeout=5)


def client_for(stack, token: str | None) -> Client:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return Client(StreamableHttpTransport(stack["url"], headers=headers))


async def test_tools_are_discoverable(stack):
    async with client_for(stack, TOKENS["management"]) as c:
        names = {t.name for t in await c.list_tools()}
    assert {
        "health_check",
        "search_notes",
        "read_note",
        "read_note_section",
        "list_directory",
        "list_recent_changes",
        "create_note",
        "append_to_note",
        "update_note_section",
        "add_inbox_item",
        "move_note",
        "rename_note",
        "archive_note",
        "restore_note",
        "set_note_status",
    } <= names


async def test_health_check_unauthenticated(stack):
    async with client_for(stack, None) as c:
        res = await c.call_tool("health_check", {})
    data = res.data
    assert data["vault_mounted"] is True
    assert set(data) == {"version", "vault_mounted", "time"}


async def test_plain_health_route_for_docker(stack):
    import httpx

    url = stack["url"].replace("/mcp", "/health")
    async with httpx.AsyncClient() as http:
        res = await http.get(url)
    assert res.status_code == 200
    assert res.json()["vault_mounted"] is True


async def test_no_token_fails(stack):
    async with client_for(stack, None) as c:
        with pytest.raises(ToolError, match="UNAUTHORIZED"):
            await c.call_tool("read_note", {"path": "50 Operations/Procedures/Cleaning.md"})


async def test_invalid_token_fails(stack):
    async with client_for(stack, "test_mgmt_totally_wrong") as c:
        with pytest.raises(ToolError, match="UNAUTHORIZED"):
            await c.call_tool("read_note", {"path": "50 Operations/Procedures/Cleaning.md"})


async def test_management_create_update_roundtrip(stack):
    async with client_for(stack, TOKENS["management"]) as c:
        created = (
            await c.call_tool(
                "create_note",
                {"path": "10 Companies/Acme.md", "content": "# Acme\n\n## Summary\n\nold\n"},
            )
        ).data
        updated = (
            await c.call_tool(
                "update_note_section",
                {
                    "path": "10 Companies/Acme.md",
                    "heading": "Summary",
                    "content": "new summary",
                    "expected_hash": created["hash"],
                },
            )
        ).data
        assert updated["hash"] != created["hash"]
        note = (await c.call_tool("read_note", {"path": "10 Companies/Acme.md"})).data
        assert "new summary" in note["content"]


async def test_staff_reads_procedures_but_cannot_write_canonical(stack):
    async with client_for(stack, TOKENS["staff"]) as c:
        note = (
            await c.call_tool("read_note", {"path": "50 Operations/Procedures/Cleaning.md"})
        ).data
        assert "Mop daily" in note["content"]
        with pytest.raises(ToolError, match="FORBIDDEN"):
            await c.call_tool(
                "create_note", {"path": "60 Finance/Hack.md", "content": "# nope\n"}
            )


async def test_staff_creates_inbox_note(stack):
    async with client_for(stack, TOKENS["staff"]) as c:
        res = (
            await c.call_tool(
                "add_inbox_item",
                {"agent_name": "staff", "title": "Pump broken", "content": "Villa 2 pump leaks."},
            )
        ).data
    assert res["path"].startswith("90 Staff Inbox/staff/")
    assert (stack["vault"] / res["path"]).exists()


async def test_search_through_http(stack):
    async with client_for(stack, TOKENS["staff"]) as c:
        res = (await c.call_tool("search_notes", {"query": "mop"})).data
    assert any(r["path"].endswith("Cleaning.md") for r in res["results"])


async def test_traversal_denied_over_http(stack):
    async with client_for(stack, TOKENS["management"]) as c:
        with pytest.raises(ToolError, match="INVALID_PATH"):
            await c.call_tool("read_note", {"path": "../secrets.md"})


async def test_writes_audited(stack):
    log = stack["audit"] / "audit.jsonl"
    assert log.exists()
    text = log.read_text()
    assert '"tool":"create_note"' in text
    assert '"client":"staff"' in text


async def test_rate_limit_triggers_429(tmp_path_factory):
    from brain_mcp.server import build_server

    base = tmp_path_factory.mktemp("ratelimit")
    vault = base / "vault"
    (vault / "10 Companies").mkdir(parents=True)
    audit = base / "audit"
    audit.mkdir()
    cfg = base / "brain.config.yaml"
    cfg.write_text(
        VALID_CONFIG.format(vault_root=vault, audit_dir=audit).replace(
            "requests_per_minute: 60", "requests_per_minute: 3"
        )
    )
    os.environ.update(TOKEN_ENV)
    server, thread, port = _start(build_server(cfg).http_app(path="/mcp"))
    try:
        client = Client(
            StreamableHttpTransport(
                f"http://127.0.0.1:{port}/mcp",
                headers={"Authorization": f"Bearer {TOKENS['management']}"},
            )
        )
        async with client:
            with pytest.raises(ToolError, match="RATE_LIMITED"):
                for _ in range(10):
                    await client.call_tool("list_directory", {"path": "/"})
    finally:
        server.should_exit = True
        thread.join(timeout=5)


async def test_tokens_never_appear_in_logs(stack, caplog):
    with caplog.at_level(logging.DEBUG):
        async with client_for(stack, TOKENS["management"]) as c:
            await c.call_tool("read_note", {"path": "50 Operations/Procedures/Cleaning.md"})
            try:
                await c.call_tool("read_note", {"path": "60 Finance/nope-missing.md"})
            except ToolError:
                pass
    for record in caplog.records:
        assert TOKENS["management"] not in record.getMessage()
