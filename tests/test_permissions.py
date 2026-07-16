import pytest

from brain_mcp.errors import PermissionDenied
from brain_mcp.permissions import PermissionEngine, glob_to_regex


@pytest.fixture
def engine(config):
    return PermissionEngine(config.roles)


class TestGlobSemantics:
    def test_double_star_crosses_directories(self):
        rx = glob_to_regex("50 Operations/**")
        assert rx.match("50 Operations/Procedures/Cleaning.md")
        assert rx.match("50 Operations/note.md")
        assert not rx.match("60 Finance/note.md")

    def test_single_star_stays_within_segment(self):
        rx = glob_to_regex("70 Meetings/*.md")
        assert rx.match("70 Meetings/standup.md")
        assert not rx.match("70 Meetings/2026/standup.md")

    def test_bad_glob_raises(self):
        with pytest.raises(ValueError):
            glob_to_regex("[unclosed")


class TestAdmin:
    def test_admin_reads_and_writes_everywhere(self, engine):
        assert engine.allowed("management", "admin", "write", "10 Companies/Acme.md")
        assert engine.allowed("management", "admin", "read", "60 Finance/2026.md")

    def test_admin_denied_audit_and_protected_system(self, engine):
        assert not engine.allowed("management", "admin", "write", "_Audit/log.jsonl")
        assert not engine.allowed(
            "management", "admin", "write", "_System/Access and Contribution Rules.md"
        )
        assert not engine.allowed("management", "admin", "write", ".obsidian/workspace.json")


class TestOperations:
    def test_ops_writes_operations_note(self, engine):
        assert engine.allowed("operations", "operations", "write", "50 Operations/Pool.md")

    def test_ops_cannot_write_finance_or_system(self, engine):
        assert not engine.allowed("operations", "operations", "write", "60 Finance/2026.md")
        assert not engine.allowed("operations", "operations", "write", "_System/Home.md")

    def test_ops_reads_system_but_not_finance(self, engine):
        assert engine.allowed("operations", "operations", "read", "_System/Entity Index.md")
        assert not engine.allowed("operations", "operations", "read", "60 Finance/2026.md")

    def test_client_placeholder_interpolates_own_inbox_only(self, engine):
        assert engine.allowed(
            "operations", "operations", "write", "90 Staff Inbox/operations/idea.md"
        )
        assert not engine.allowed(
            "operations", "operations", "write", "90 Staff Inbox/staff/idea.md"
        )


class TestStaff:
    def test_staff_reads_procedures(self, engine):
        assert engine.allowed("staff", "staff", "read", "50 Operations/Procedures/Cleaning.md")

    def test_staff_cannot_read_operations_outside_procedures(self, engine):
        assert not engine.allowed("staff", "staff", "read", "50 Operations/Suppliers.md")

    def test_staff_writes_own_inbox_only(self, engine):
        assert engine.allowed("staff", "staff", "write", "90 Staff Inbox/staff/report.md")
        assert not engine.allowed("staff", "staff", "write", "50 Operations/Procedures/Cleaning.md")
        assert not engine.allowed("staff", "staff", "write", "10 Companies/Acme.md")

    def test_write_grant_implies_read_of_own_inbox(self, engine):
        # staff must be able to read back what they are allowed to write
        assert engine.allowed("staff", "staff", "read", "90 Staff Inbox/staff/report.md")


class TestDefaults:
    def test_default_deny_when_nothing_matches(self, engine):
        assert not engine.allowed("staff", "staff", "read", "80 Decisions/Big.md")

    def test_deny_beats_write(self, engine):
        assert not engine.allowed("operations", "operations", "write", "_Audit/x.md")

    def test_unknown_role_denies(self, engine):
        assert not engine.allowed("x", "ghost-role", "read", "10 Companies/Acme.md")

    def test_require_raises_structured_error(self, engine):
        with pytest.raises(PermissionDenied):
            engine.require("staff", "staff", "write", "60 Finance/2026.md")
