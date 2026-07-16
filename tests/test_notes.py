import pytest

from brain_mcp.auth import Client
from brain_mcp.errors import (
    AlreadyExists,
    Conflict,
    NotFound,
    PermissionDenied,
    TooLarge,
)
from brain_mcp.notes import VaultService

MGMT = Client(name="management", role="admin")
OPS = Client(name="operations", role="operations")
STAFF = Client(name="staff", role="staff")


@pytest.fixture
def svc(config, tmp_path):
    return VaultService(config)


class TestCreate:
    def test_create_injects_frontmatter(self, svc, vault):
        res = svc.create_note(OPS, "50 Operations/Pool.md", "# Pool\n\nNotes.\n")
        text = (vault / "50 Operations" / "Pool.md").read_text()
        assert text.startswith("---\n")
        assert "author_agent: operations" in text
        assert "status: unverified" in text
        assert "created:" in text
        assert res["hash"]

    def test_create_preserves_existing_frontmatter_fields(self, svc, vault):
        svc.create_note(OPS, "50 Operations/Spa.md", "---\ntype: procedure\n---\n# Spa\n")
        text = (vault / "50 Operations" / "Spa.md").read_text()
        assert "type: procedure" in text
        assert "status: unverified" in text

    def test_create_existing_fails(self, svc):
        svc.create_note(OPS, "50 Operations/Dup.md", "# Dup\n")
        with pytest.raises(AlreadyExists):
            svc.create_note(OPS, "50 Operations/Dup.md", "# Dup again\n")

    def test_create_denied_outside_role(self, svc):
        with pytest.raises(PermissionDenied):
            svc.create_note(STAFF, "60 Finance/Sneaky.md", "# nope\n")

    def test_create_too_large_fails(self, svc, config):
        big = "x" * (config.limits.max_note_bytes + 1)
        with pytest.raises(TooLarge):
            svc.create_note(OPS, "50 Operations/Big.md", big)

    def test_create_makes_intermediate_dirs(self, svc, vault):
        svc.create_note(OPS, "50 Operations/2026/July/Note.md", "# ok\n")
        assert (vault / "50 Operations" / "2026" / "July" / "Note.md").exists()


class TestReadAndSections:
    def test_read_roundtrip(self, svc):
        created = svc.create_note(OPS, "50 Operations/R.md", "# R\n\nbody\n")
        res = svc.read_note(OPS, "50 Operations/R.md")
        assert "body" in res["content"]
        assert res["hash"] == created["hash"]

    def test_read_missing_raises_not_found(self, svc):
        with pytest.raises(NotFound):
            svc.read_note(OPS, "50 Operations/NoSuch.md")

    def test_read_denied_by_role(self, svc):
        svc.create_note(MGMT, "60 Finance/Q3.md", "# Q3\n")
        with pytest.raises(PermissionDenied):
            svc.read_note(STAFF, "60 Finance/Q3.md")

    def test_read_section(self, svc):
        svc.create_note(
            OPS, "50 Operations/S.md", "# S\n\n## Steps\n\n1. one\n\n## Related\n\nnone\n"
        )
        res = svc.read_note_section(OPS, "50 Operations/S.md", "Steps")
        assert "1. one" in res["content"]
        assert "none" not in res["content"]

    def test_read_section_missing_heading(self, svc):
        svc.create_note(OPS, "50 Operations/S2.md", "# S2\n")
        with pytest.raises(NotFound):
            svc.read_note_section(OPS, "50 Operations/S2.md", "Ghost")


class TestUpdateSection:
    def test_update_section_with_correct_hash(self, svc):
        c = svc.create_note(OPS, "50 Operations/U.md", "# U\n\n## Steps\n\nold\n\n## End\n\nfin\n")
        res = svc.update_note_section(OPS, "50 Operations/U.md", "Steps", "new steps", c["hash"])
        body = svc.read_note(OPS, "50 Operations/U.md")["content"]
        assert "new steps" in body and "old" not in body
        assert "fin" in body  # later sections untouched
        assert res["hash"] != c["hash"]

    def test_update_section_stale_hash_conflicts(self, svc):
        c = svc.create_note(OPS, "50 Operations/U2.md", "# U\n\n## Steps\n\nold\n")
        svc.update_note_section(OPS, "50 Operations/U2.md", "Steps", "first", c["hash"])
        with pytest.raises(Conflict):
            svc.update_note_section(OPS, "50 Operations/U2.md", "Steps", "second", c["hash"])

    def test_update_section_requires_hash(self, svc):
        svc.create_note(OPS, "50 Operations/U3.md", "# U\n\n## Steps\n\nold\n")
        with pytest.raises(TypeError):
            svc.update_note_section(OPS, "50 Operations/U3.md", "Steps", "x")


class TestAppend:
    def test_append_adds_content(self, svc):
        svc.create_note(OPS, "50 Operations/A.md", "# A\n")
        svc.append_to_note(OPS, "50 Operations/A.md", "- appended line")
        assert "- appended line" in svc.read_note(OPS, "50 Operations/A.md")["content"]

    def test_append_with_stale_hash_conflicts(self, svc):
        c = svc.create_note(OPS, "50 Operations/A2.md", "# A\n")
        svc.append_to_note(OPS, "50 Operations/A2.md", "one")
        with pytest.raises(Conflict):
            svc.append_to_note(OPS, "50 Operations/A2.md", "two", expected_hash=c["hash"])


class TestInbox:
    def test_staff_adds_inbox_item(self, svc, vault):
        res = svc.add_inbox_item(STAFF, "staff", "Broken pump", "Pump at villa 2 leaking")
        assert res["path"].startswith("90 Staff Inbox/staff/")
        assert (vault / res["path"]).exists()

    def test_staff_cannot_add_to_other_inbox(self, svc):
        with pytest.raises(PermissionDenied):
            svc.add_inbox_item(STAFF, "operations", "Sneaky", "nope")


class TestMoveArchiveRestore:
    def test_move_note(self, svc, vault):
        svc.create_note(MGMT, "10 Companies/Old.md", "# Old\n")
        svc.move_note(MGMT, "10 Companies/Old.md", "10 Companies/New.md")
        assert not (vault / "10 Companies" / "Old.md").exists()
        assert (vault / "10 Companies" / "New.md").exists()

    def test_move_onto_existing_fails(self, svc):
        svc.create_note(MGMT, "10 Companies/M1.md", "# 1\n")
        svc.create_note(MGMT, "10 Companies/M2.md", "# 2\n")
        with pytest.raises(AlreadyExists):
            svc.move_note(MGMT, "10 Companies/M1.md", "10 Companies/M2.md")

    def test_archive_and_restore_admin_only(self, svc, vault):
        svc.create_note(MGMT, "10 Companies/Gone.md", "# Gone\n")
        svc.archive_note(MGMT, "10 Companies/Gone.md")
        assert not (vault / "10 Companies" / "Gone.md").exists()
        assert (vault / "_Archive" / "10 Companies" / "Gone.md").exists()
        svc.restore_note(MGMT, "10 Companies/Gone.md")
        assert (vault / "10 Companies" / "Gone.md").exists()

    def test_non_admin_cannot_archive(self, svc):
        svc.create_note(OPS, "50 Operations/Keep.md", "# Keep\n")
        with pytest.raises(PermissionDenied):
            svc.archive_note(OPS, "50 Operations/Keep.md")


class TestListing:
    def test_list_directory(self, svc):
        svc.create_note(OPS, "50 Operations/L1.md", "# 1\n")
        entries = svc.list_directory(OPS, "50 Operations")
        names = [e["name"] for e in entries]
        assert "L1.md" in names and "Procedures" in names

    def test_list_directory_hides_dot_entries(self, svc, vault):
        (vault / ".obsidian").mkdir(exist_ok=True)
        entries = svc.list_directory(MGMT, "/")
        assert all(not e["name"].startswith(".") for e in entries)

    def test_list_recent_changes(self, svc):
        svc.create_note(OPS, "50 Operations/Fresh.md", "# fresh\n")
        res = svc.list_recent_changes(OPS, days=1, limit=10)
        assert any(r["path"] == "50 Operations/Fresh.md" for r in res)

    def test_recent_changes_respects_read_permission(self, svc):
        svc.create_note(MGMT, "60 Finance/Secret.md", "# s\n")
        res = svc.list_recent_changes(STAFF, days=1, limit=50)
        assert not any("60 Finance" in r["path"] for r in res)


class TestStatusPromotion:
    def test_admin_promotes_to_canonical(self, svc, vault):
        svc.create_note(OPS, "50 Operations/P.md", "# P\n")
        svc.set_note_status(MGMT, "50 Operations/P.md", "canonical")
        assert "status: canonical" in (vault / "50 Operations" / "P.md").read_text()

    def test_non_admin_cannot_promote(self, svc):
        svc.create_note(OPS, "50 Operations/P2.md", "# P\n")
        with pytest.raises(PermissionDenied):
            svc.set_note_status(OPS, "50 Operations/P2.md", "canonical")
