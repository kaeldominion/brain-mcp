import pytest

from brain_mcp.auth import Client
from brain_mcp.notes import VaultService
from brain_mcp.search import SearchEngine

MGMT = Client(name="management", role="admin")
STAFF = Client(name="staff", role="staff")


@pytest.fixture
def svc(config):
    s = VaultService(config)
    s.create_note(
        MGMT,
        "50 Operations/Procedures/Pool Cleaning.md",
        "# Pool Cleaning\n\n## Steps\n\nSkim the pool surface daily with the long net.\n",
    )
    s.create_note(
        MGMT,
        "60 Finance/Budget 2026.md",
        "# Budget 2026\n\nPool maintenance budget is 500 per month.\n",
    )
    return s


@pytest.fixture
def engine(config, svc):
    return SearchEngine(config)


def test_search_finds_matches_with_required_fields(engine, svc):
    results = engine.search(svc.perms, MGMT, "pool")
    assert len(results) >= 2
    r = results[0]
    for field in ("path", "title", "excerpt", "headings", "modified"):
        assert field in r
    assert any("Pool Cleaning" in (r["title"] or "") for r in results)


def test_search_excerpt_contains_match(engine, svc):
    results = engine.search(svc.perms, MGMT, "long net")
    assert results
    assert "long net" in results[0]["excerpt"].lower()


def test_search_respects_role_read_permissions(engine, svc):
    results = engine.search(svc.perms, STAFF, "pool")
    paths = [r["path"] for r in results]
    assert "50 Operations/Procedures/Pool Cleaning.md" in paths
    assert not any(p.startswith("60 Finance") for p in paths)


def test_search_folder_filter(engine, svc):
    results = engine.search(svc.perms, MGMT, "pool", folder="60 Finance")
    assert results
    assert all(r["path"].startswith("60 Finance") for r in results)


def test_search_limit(engine, svc):
    results = engine.search(svc.perms, MGMT, "pool", limit=1)
    assert len(results) == 1


def test_search_no_results(engine, svc):
    assert engine.search(svc.perms, MGMT, "zzz-nonexistent-term") == []


def test_python_fallback_matches_ripgrep_contract(config, svc):
    engine = SearchEngine(config, use_ripgrep=False)
    results = engine.search(svc.perms, MGMT, "pool")
    assert len(results) >= 2
    assert all("excerpt" in r for r in results)
