from concurrent.futures import ThreadPoolExecutor

import pytest

from brain_mcp.auth import Client
from brain_mcp.errors import Conflict
from brain_mcp.notes import VaultService

OPS = Client(name="operations", role="operations")
MGMT = Client(name="management", role="admin")


@pytest.fixture
def svc(config):
    return VaultService(config)


def test_concurrent_appends_lose_nothing(svc):
    svc.create_note(OPS, "50 Operations/Log.md", "# Log\n")
    n = 40

    def append(i):
        svc.append_to_note(OPS, "50 Operations/Log.md", f"- entry {i}")

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(append, range(n)))

    content = svc.read_note(OPS, "50 Operations/Log.md")["content"]
    for i in range(n):
        assert f"- entry {i}" in content, f"lost append {i}"


def test_concurrent_reads_work(svc):
    svc.create_note(OPS, "50 Operations/RR.md", "# RR\n\ncontent\n")

    def read(_):
        return svc.read_note(OPS, "50 Operations/RR.md")["content"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(read, range(32)))
    assert all("content" in r for r in results)


def test_conflicting_section_updates_conflict_not_overwrite(svc):
    c = svc.create_note(OPS, "50 Operations/CS.md", "# CS\n\n## Steps\n\nv0\n")
    h = c["hash"]

    results = []

    def update(text):
        try:
            svc.update_note_section(OPS, "50 Operations/CS.md", "Steps", text, h)
            results.append(("ok", text))
        except Conflict:
            results.append(("conflict", text))

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(update, ["writer-a", "writer-b"]))

    outcomes = sorted(r[0] for r in results)
    assert outcomes == ["conflict", "ok"], f"expected exactly one winner, got {results}"
    content = svc.read_note(OPS, "50 Operations/CS.md")["content"]
    winner = next(t for s, t in results if s == "ok")
    assert winner in content


def test_concurrent_creates_only_one_wins(svc):
    from brain_mcp.errors import AlreadyExists

    outcomes = []

    def create(i):
        try:
            svc.create_note(OPS, "50 Operations/Race.md", f"# from {i}\n")
            outcomes.append("ok")
        except AlreadyExists:
            outcomes.append("exists")

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(create, range(4)))

    assert outcomes.count("ok") == 1
