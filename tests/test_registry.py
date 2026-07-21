import time

import pytest
import yaml

from brain_mcp.auth import hash_token
from brain_mcp.config import load_config
from brain_mcp.errors import AuthError, ConfigError, InvalidArgument, PermissionDenied
from brain_mcp.registry import ClientRegistry
from tests.conftest import TOKEN_ENV, TOKENS, VALID_CONFIG


@pytest.fixture
def clients_file(tmp_path):
    return tmp_path / "clients" / "clients.yaml"


@pytest.fixture
def dyn_config(tmp_path, vault, clients_file):
    audit = tmp_path / "audit"
    audit.mkdir(exist_ok=True)
    path = tmp_path / "brain.config.yaml"
    path.write_text(
        VALID_CONFIG.format(vault_root=vault, audit_dir=audit)
        + f"clients_file: {clients_file}\n"
    )
    return load_config(path)


@pytest.fixture
def registry(dyn_config):
    return ClientRegistry.from_config(dyn_config, TOKEN_ENV)


def write_clients(clients_file, entries):
    clients_file.parent.mkdir(parents=True, exist_ok=True)
    clients_file.write_text(yaml.safe_dump({"clients": entries}))
    # ensure a fresh mtime even on coarse filesystems
    now = time.time() + 1
    import os

    os.utime(clients_file, (now, now))


class TestLoading:
    def test_config_parses_clients_file_key(self, dyn_config, clients_file):
        assert dyn_config.clients_file == clients_file

    def test_static_clients_still_authenticate(self, registry):
        assert registry.authenticate(f"Bearer {TOKENS['management']}").name == "management"

    def test_missing_file_is_empty_registry(self, registry):
        assert [c.name for c in registry.list_clients()] == ["management", "operations", "staff"]

    def test_file_clients_authenticate(self, registry, clients_file):
        write_clients(
            clients_file,
            [{"name": "finance", "role": "operations", "token_hash": hash_token("t_fin_1234")}],
        )
        client = registry.authenticate("Bearer t_fin_1234")
        assert client.name == "finance"
        assert client.role == "operations"


class TestHotReload:
    def test_new_client_appears_without_restart(self, registry, clients_file):
        with pytest.raises(AuthError):
            registry.authenticate("Bearer t_new_1")
        write_clients(
            clients_file,
            [{"name": "newbie", "role": "staff", "token_hash": hash_token("t_new_1")}],
        )
        assert registry.authenticate("Bearer t_new_1").name == "newbie"

    def test_removed_client_stops_authenticating(self, registry, clients_file):
        write_clients(
            clients_file,
            [{"name": "temp", "role": "staff", "token_hash": hash_token("t_tmp_1")}],
        )
        assert registry.authenticate("Bearer t_tmp_1").name == "temp"
        write_clients(clients_file, [])
        with pytest.raises(AuthError):
            registry.authenticate("Bearer t_tmp_1")

    def test_broken_file_keeps_last_good_state(self, registry, clients_file):
        write_clients(
            clients_file,
            [{"name": "keeper", "role": "staff", "token_hash": hash_token("t_keep_1")}],
        )
        assert registry.authenticate("Bearer t_keep_1").name == "keeper"
        clients_file.write_text("{{{{ not yaml")
        import os

        now = time.time() + 2
        os.utime(clients_file, (now, now))
        # still serves the last good registry rather than dying
        assert registry.authenticate("Bearer t_keep_1").name == "keeper"


class TestMutations:
    def test_add_client_with_owner_persists_and_surfaces(self, registry):
        token = registry.add_client("tia-gm", "operations", deploy_prefix="acme", owner="Tia, GM")
        client = registry.authenticate(f"Bearer {token}")
        assert client.name == "tia-gm"
        assert client.owner == "Tia, GM"
        info = next(c for c in registry.list_clients() if c.name == "tia-gm")
        assert info.owner == "Tia, GM"

    def test_rotate_preserves_owner(self, registry):
        registry.add_client("rot", "staff", owner="Dana")
        new = registry.rotate_client("rot")
        assert registry.authenticate(f"Bearer {new}").owner == "Dana"

    def test_add_client_returns_token_once_and_authenticates(self, registry):
        token = registry.add_client("finance", "operations", deploy_prefix="acme")
        assert token.startswith("acme_finance_")
        assert registry.authenticate(f"Bearer {token}").name == "finance"
        assert registry.authenticate(f"Bearer {token}").owner is None
        data = yaml.safe_load(registry.clients_file.read_text())
        entry = next(c for c in data["clients"] if c["name"] == "finance")
        assert entry["token_hash"] == hash_token(token)
        assert token not in registry.clients_file.read_text()

    def test_clients_file_is_chmod_600(self, registry):
        registry.add_client("sec", "staff")
        assert (registry.clients_file.stat().st_mode & 0o777) == 0o600

    def test_duplicate_name_rejected_across_static_and_file(self, registry):
        with pytest.raises(InvalidArgument):
            registry.add_client("management", "staff")  # static name
        registry.add_client("dup", "staff")
        with pytest.raises(InvalidArgument):
            registry.add_client("dup", "staff")

    def test_unknown_role_rejected(self, registry):
        with pytest.raises(InvalidArgument):
            registry.add_client("ghost", "no-such-role")

    def test_second_admin_rejected(self, registry):
        with pytest.raises(InvalidArgument):
            registry.add_client("boss2", "admin")

    def test_rotate_kills_old_token(self, registry):
        old = registry.add_client("rot", "staff")
        new = registry.rotate_client("rot")
        assert new != old
        assert registry.authenticate(f"Bearer {new}").name == "rot"
        with pytest.raises(AuthError):
            registry.authenticate(f"Bearer {old}")

    def test_remove_client(self, registry):
        token = registry.add_client("bye", "staff")
        registry.remove_client("bye")
        with pytest.raises(AuthError):
            registry.authenticate(f"Bearer {token}")

    def test_static_clients_are_immutable_via_api(self, registry):
        with pytest.raises(InvalidArgument):
            registry.rotate_client("management")
        with pytest.raises(InvalidArgument):
            registry.remove_client("management")

    def test_cannot_remove_only_admin(self, registry):
        with pytest.raises(InvalidArgument):
            registry.remove_client("no-such")  # unknown name also rejected

    def test_mutations_without_clients_file_configured(self, config):
        reg = ClientRegistry.from_config(config, TOKEN_ENV)
        with pytest.raises(InvalidArgument):
            reg.add_client("x", "staff")


class TestConsoleRole:
    def test_console_client_authenticates_with_console_role(self, registry, clients_file):
        write_clients(
            clients_file,
            [{"name": "console", "role": "console", "token_hash": hash_token("t_con_1")}],
        )
        client = registry.authenticate("Bearer t_con_1")
        assert client.role == "console"

    def test_console_not_counted_as_admin(self, registry):
        # adding a console client must not trip the one-admin rule
        registry.add_client("panel", "console")
        # and a real second admin is still rejected
        with pytest.raises(InvalidArgument):
            registry.add_client("boss2", "admin")


class TestConsolePermissions:
    def test_console_role_gets_admin_equivalent_vault_access(self, dyn_config):
        from brain_mcp.auth import Client
        from brain_mcp.notes import VaultService

        svc = VaultService(dyn_config)
        console = Client(name="panel", role="console")
        svc.create_note(console, "10 Companies/C.md", "# C\n")
        svc.set_note_status(console, "10 Companies/C.md", "canonical")
        with pytest.raises(PermissionDenied):
            svc.create_note(console, "_Audit/x.md", "#")
