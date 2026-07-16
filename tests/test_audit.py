import json

import pytest

from brain_mcp.audit import Auditor
from brain_mcp.auth import Client
from brain_mcp.notes import VaultService

MGMT = Client(name="management", role="admin")
STAFF = Client(name="staff", role="staff")


@pytest.fixture
def audit_dir(config):
    return config.audit_dir


@pytest.fixture
def auditor(config):
    return Auditor(config.audit_dir, max_bytes=100_000, keep=3)


@pytest.fixture
def svc(config, auditor):
    return VaultService(config, audit_hook=auditor.record)


def read_events(audit_dir):
    log = audit_dir / "audit.jsonl"
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_successful_write_creates_audit_event(svc, audit_dir):
    svc.create_note(MGMT, "10 Companies/A.md", "# A\n")
    events = read_events(audit_dir)
    assert len(events) == 1
    e = events[0]
    assert e["client"] == "management"
    assert e["role"] == "admin"
    assert e["tool"] == "create_note"
    assert e["path"] == "10 Companies/A.md"
    assert e["ok"] is True
    assert e["after_hash"]
    assert e["ts"].endswith("Z")


def test_denied_write_creates_audit_event(svc, audit_dir):
    from brain_mcp.errors import PermissionDenied

    with pytest.raises(PermissionDenied):
        svc.create_note(STAFF, "60 Finance/X.md", "# nope\n")
    events = read_events(audit_dir)
    assert len(events) == 1
    assert events[0]["ok"] is False
    assert events[0]["error"]


def test_update_records_before_and_after_hashes(svc, audit_dir):
    c = svc.create_note(MGMT, "10 Companies/B.md", "# B\n\n## S\n\nx\n")
    svc.update_note_section(MGMT, "10 Companies/B.md", "S", "y", c["hash"])
    e = read_events(audit_dir)[-1]
    assert e["before_hash"] == c["hash"]
    assert e["after_hash"] != c["hash"]


def test_rotation_keeps_bounded_files(config):
    auditor = Auditor(config.audit_dir, max_bytes=500, keep=2)
    for i in range(200):
        auditor.record({"ts": "t", "client": "c", "tool": "t", "path": f"p{i}", "ok": True})
    files = sorted(p.name for p in config.audit_dir.glob("audit*.jsonl"))
    assert "audit.jsonl" in files
    assert len(files) <= 3  # active + keep


def test_audit_appends_are_thread_safe(config):
    from concurrent.futures import ThreadPoolExecutor

    auditor = Auditor(config.audit_dir, max_bytes=10_000_000, keep=2)

    def rec(i):
        auditor.record({"ts": "t", "client": "c", "tool": "t", "path": f"p{i}", "ok": True})

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(rec, range(100)))

    lines = (config.audit_dir / "audit.jsonl").read_text().splitlines()
    assert len(lines) == 100
    assert all(json.loads(line) for line in lines)
