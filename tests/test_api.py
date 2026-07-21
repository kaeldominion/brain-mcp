"""Admin/console REST API tests over real HTTP (uvicorn + httpx)."""

import hashlib
import os
import socket
import threading
import time

import httpx
import pytest
import uvicorn

from tests.conftest import VALID_CONFIG

pytestmark = pytest.mark.integration

ADMIN_TOKEN = "test_admin_" + "a" * 32
CONSOLE_TOKEN = "test_console_" + "b" * 32
STAFF_TOKEN = "test_staffer_" + "c" * 32


def _h(t):
    return hashlib.sha256(t.encode()).hexdigest()


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def api(tmp_path_factory):
    from brain_mcp.server import build_server

    base = tmp_path_factory.mktemp("api")
    vault = base / "vault"
    for d in ["_System", "10 Companies", "50 Operations/Procedures", "60 Finance",
              "90 Staff Inbox/staffer", "_Archive"]:
        (vault / d).mkdir(parents=True)
    (vault / "_System" / "Home.md").write_text("---\nstatus: canonical\n---\n# Home\n")
    (vault / "10 Companies" / "Acme.md").write_text(
        "---\nstatus: unverified\nauthor_agent: staffer\ncreated: 2026-07-16T00:00:00Z\n---\n# Acme\n"
    )
    (vault / "90 Staff Inbox" / "staffer" / "2026-07-16 pump.md").write_text(
        "---\nstatus: unverified\nauthor_agent: staffer\n---\n# Pump broken\n"
    )
    audit = base / "audit"
    audit.mkdir()
    cfg = base / "brain.config.yaml"
    cfg.write_text(
        VALID_CONFIG.format(vault_root=vault, audit_dir=audit)
        .replace(
            "clients:",
            "clients:\n"
            "  - name: apiadmin\n"
            "    token_hash_env: T_APIADMIN\n"
            "    role: admin\n"
            "  - name: panel\n"
            "    token_hash_env: T_PANEL\n"
            "    role: console\n"
            "  - name: staffer\n"
            "    token_hash_env: T_STAFFER\n"
            "    role: staff\n",
            1,
        )
        .replace("  - name: management\n    token_hash_env: MCP_TOKEN_HASH_MANAGEMENT\n    role: admin\n", "")
        + f"clients_file: {base / 'clients' / 'clients.yaml'}\n"
    )
    os.environ.update(
        {
            "T_APIADMIN": _h(ADMIN_TOKEN),
            "T_PANEL": _h(CONSOLE_TOKEN),
            "T_STAFFER": _h(STAFF_TOKEN),
            "MCP_TOKEN_HASH_OPERATIONS": _h("x_ops_" + "d" * 32),
            "MCP_TOKEN_HASH_STAFF": _h("x_staff_" + "e" * 32),
        }
    )
    mcp = build_server(cfg)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(mcp.http_app(path="/mcp"), host="127.0.0.1",
                                           port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started:
        if time.time() > deadline:
            raise RuntimeError("uvicorn did not start")
        time.sleep(0.02)
    yield {"base": f"http://127.0.0.1:{port}", "vault": vault, "audit": audit}
    server.should_exit = True
    thread.join(timeout=5)


def get(api, path, token=None, **kw):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.get(api["base"] + path, headers=headers, **kw)


def post(api, path, token=None, json=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.post(api["base"] + path, headers=headers, json=json)


class TestAuth:
    def test_health_is_public(self, api):
        r = get(api, "/api/health")
        assert r.status_code == 200
        assert r.json()["vault_mounted"] is True

    def test_no_token_is_401(self, api):
        assert get(api, "/api/stats").status_code == 401

    def test_agent_token_is_403(self, api):
        assert get(api, "/api/stats", STAFF_TOKEN).status_code == 403

    def test_console_and_admin_allowed(self, api):
        assert get(api, "/api/stats", CONSOLE_TOKEN).status_code == 200
        assert get(api, "/api/stats", ADMIN_TOKEN).status_code == 200


class TestStatsAndReview:
    def test_stats_counts(self, api):
        s = get(api, "/api/stats", CONSOLE_TOKEN).json()
        assert s["notes_total"] >= 3
        assert s["unverified"] >= 2
        assert s["inbox_items"] >= 1
        assert "10 Companies" in s["by_folder"]

    def test_review_lists_unverified_and_inbox(self, api):
        items = get(api, "/api/review", CONSOLE_TOKEN).json()["items"]
        paths = [i["path"] for i in items]
        assert "10 Companies/Acme.md" in paths
        assert any(p.startswith("90 Staff Inbox/") for p in paths)
        acme = next(i for i in items if i["path"] == "10 Companies/Acme.md")
        assert acme["author_agent"] == "staffer"
        assert acme["title"] == "Acme"

    def test_note_read(self, api):
        r = get(api, "/api/note", CONSOLE_TOKEN, params={"path": "10 Companies/Acme.md"})
        assert r.status_code == 200
        assert "# Acme" in r.json()["content"]

    def test_promote_then_gone_from_review(self, api):
        r = post(api, "/api/notes/promote", CONSOLE_TOKEN, {"path": "10 Companies/Acme.md"})
        assert r.status_code == 200
        assert "status: canonical" in (api["vault"] / "10 Companies" / "Acme.md").read_text()
        paths = [i["path"] for i in get(api, "/api/review", CONSOLE_TOKEN).json()["items"]]
        assert "10 Companies/Acme.md" not in paths

    def test_archive_inbox_item(self, api):
        path = "90 Staff Inbox/staffer/2026-07-16 pump.md"
        r = post(api, "/api/notes/archive", CONSOLE_TOKEN, {"path": path})
        assert r.status_code == 200
        assert (api["vault"] / "_Archive" / path).exists()

    def test_promote_missing_is_404(self, api):
        r = post(api, "/api/notes/promote", CONSOLE_TOKEN, {"path": "60 Finance/nope.md"})
        assert r.status_code == 404
        assert r.json()["error"] == "NOT_FOUND"


class TestVaultBrowsing:
    def test_list_root(self, api):
        r = get(api, "/api/list", CONSOLE_TOKEN, params={"path": "/"})
        assert r.status_code == 200
        names = [e["name"] for e in r.json()["entries"]]
        assert "10 Companies" in names and "_System" in names

    def test_list_requires_auth(self, api):
        assert get(api, "/api/list", params={"path": "/"}).status_code == 401

    def test_search(self, api):
        r = get(api, "/api/search", CONSOLE_TOKEN, params={"q": "Acme"})
        assert r.status_code == 200
        assert any(hit["path"] == "10 Companies/Acme.md" for hit in r.json()["results"])


class TestIdentity:
    def test_generic_home_yields_no_name(self, api):
        (api["vault"] / "_System" / "Company 2nd Brain Home.md").write_text(
            "# Company 2nd Brain Home\n\nWelcome.\n"
        )
        r = get(api, "/api/identity", CONSOLE_TOKEN).json()
        assert r["name"] is None

    def test_personalized_home_yields_name_and_about(self, api):
        (api["vault"] / "_System" / "Company 2nd Brain Home.md").write_text(
            "---\nstatus: canonical\n---\n"
            "# Acme Villas — 2nd Brain\n\n"
            "## About\n\n"
            "Acme Villas manages 14 rental properties in Bali.\nFounded 2020.\n\n"
            "## Map\n\ntable here\n"
        )
        r = get(api, "/api/identity", CONSOLE_TOKEN).json()
        assert r["name"] == "Acme Villas — 2nd Brain"
        assert "14 rental properties" in r["about"]
        assert "table here" not in r["about"]

    def test_identity_requires_auth(self, api):
        assert get(api, "/api/identity").status_code == 401


class TestOnboardingStatus:
    def test_no_protocol_note_means_not_started(self, api):
        s = get(api, "/api/stats", CONSOLE_TOKEN).json()
        assert s["onboarding"] == {"phase": None, "complete": False, "sessions": 0}

    def test_phase_parsed_from_session_log(self, api):
        (api["vault"] / "_System" / "Onboarding Protocol.md").write_text(
            "# Onboarding Protocol\n\n## Phase 0 — Orientation\n\ninstructions\n\n"
            "## Session log\n\n"
            "- 2026-07-16 — Phase 1 reached, 6 notes created\n"
            "- 2026-07-17 — Phase 3 reached, 14 notes created\n"
        )
        s = get(api, "/api/stats", CONSOLE_TOKEN).json()
        assert s["onboarding"]["phase"] == 3
        assert s["onboarding"]["complete"] is False
        assert s["onboarding"]["sessions"] == 2

    def test_complete_detected(self, api):
        p = api["vault"] / "_System" / "Onboarding Protocol.md"
        p.write_text(
            p.read_text() + "- 2026-07-18 — Phase 6 review confirmed. Onboarding complete.\n"
        )
        s = get(api, "/api/stats", CONSOLE_TOKEN).json()
        assert s["onboarding"]["phase"] == 6
        assert s["onboarding"]["complete"] is True


class TestGraph:
    def test_graph_nodes_and_wikilink_edges(self, api):
        (api["vault"] / "20 People").mkdir(exist_ok=True)
        (api["vault"] / "20 People" / "Jane Doe.md").write_text(
            "---\nstatus: unverified\n---\n# Jane Doe\n\nWorks at [[Acme]].\n"
        )
        r = get(api, "/api/graph", CONSOLE_TOKEN)
        assert r.status_code == 200
        data = r.json()
        ids = {n["id"] for n in data["nodes"]}
        assert "20 People/Jane Doe.md" in ids
        assert "10 Companies/Acme.md" in ids
        assert {"source": "20 People/Jane Doe.md", "target": "10 Companies/Acme.md"} in [
            {"source": e["source"], "target": e["target"]} for e in data["edges"]
        ]
        jane = next(n for n in data["nodes"] if n["id"] == "20 People/Jane Doe.md")
        assert jane["folder"] == "20 People"
        assert jane["title"] == "Jane Doe"

    def test_graph_requires_auth(self, api):
        assert get(api, "/api/graph").status_code == 401


class TestClients:
    def test_list_clients(self, api):
        r = get(api, "/api/clients", CONSOLE_TOKEN)
        names = {c["name"] for c in r.json()["clients"]}
        assert {"apiadmin", "panel", "staffer"} <= names

    def test_roles_from_config_excludes_admin(self, api):
        # returns THIS install's actual roles (the fixture defines operations/staff)
        roles = get(api, "/api/roles", CONSOLE_TOKEN).json()["roles"]
        assert "admin" not in roles
        assert "operations" in roles and "staff" in roles

    def test_create_rotate_revoke_lifecycle(self, api):
        r = post(api, "/api/clients", CONSOLE_TOKEN,
                 {"name": "fieldbot", "role": "staff", "deploy_prefix": "acme"})
        assert r.status_code == 200
        token = r.json()["token"]
        assert token.startswith("acme_fieldbot_")
        # the new token authenticates (agent role → 403 on admin API proves auth works)
        assert get(api, "/api/stats", token).status_code == 403

        r2 = post(api, "/api/clients/fieldbot/rotate", CONSOLE_TOKEN)
        token2 = r2.json()["token"]
        assert token2 != token
        assert get(api, "/api/stats", token).status_code == 401  # old token dead

        r3 = httpx.delete(api["base"] + "/api/clients/fieldbot",
                          headers={"Authorization": f"Bearer {CONSOLE_TOKEN}"})
        assert r3.status_code == 200
        assert get(api, "/api/stats", token2).status_code == 401

    def test_second_admin_rejected(self, api):
        r = post(api, "/api/clients", CONSOLE_TOKEN, {"name": "boss2", "role": "admin"})
        assert r.status_code == 400

    def test_static_client_immutable(self, api):
        r = post(api, "/api/clients/staffer/rotate", CONSOLE_TOKEN)
        assert r.status_code == 400


class TestAudit:
    def test_audit_lists_events_with_filters(self, api):
        events = get(api, "/api/audit", CONSOLE_TOKEN).json()["events"]
        assert any(e["tool"] == "set_note_status" for e in events)
        only = get(api, "/api/audit", CONSOLE_TOKEN,
                   params={"tool": "archive_note"}).json()["events"]
        assert only and all(e["tool"] == "archive_note" for e in only)
