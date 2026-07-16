from pathlib import Path

import pytest

from brain_mcp.config import ConfigError, load_config
from tests.conftest import write_config


def test_valid_config_loads(config, vault):
    assert config.vault_root == Path(vault)
    assert [c.name for c in config.clients] == ["management", "operations", "staff"]
    assert config.clients[0].role == "admin"
    assert set(config.roles) == {"admin", "operations", "staff"}
    assert config.limits.requests_per_minute == 60
    assert config.limits.max_note_bytes == 1048576


def test_limits_have_defaults(tmp_path, vault):
    path = write_config(
        tmp_path,
        f"""\
        vault_root: {vault}
        audit_dir: {tmp_path / 'audit'}
        clients:
          - name: a
            token_hash_env: T_A
            role: admin
        roles:
          admin:
            read: ["**"]
            write: ["**"]
            deny: []
        """,
    )
    cfg = load_config(path)
    assert cfg.limits.requests_per_minute == 60
    assert cfg.limits.max_note_bytes == 1048576


def test_unknown_role_refuses_boot(tmp_path, vault):
    path = write_config(
        tmp_path,
        f"""\
        vault_root: {vault}
        audit_dir: {tmp_path / 'audit'}
        clients:
          - name: a
            token_hash_env: T_A
            role: nonexistent
        roles:
          admin: {{read: ["**"], write: ["**"], deny: []}}
        """,
    )
    with pytest.raises(ConfigError, match="nonexistent"):
        load_config(path)


def test_duplicate_client_names_refuse_boot(tmp_path, vault):
    path = write_config(
        tmp_path,
        f"""\
        vault_root: {vault}
        audit_dir: {tmp_path / 'audit'}
        clients:
          - {{name: a, token_hash_env: T_A, role: admin}}
          - {{name: a, token_hash_env: T_B, role: admin}}
        roles:
          admin: {{read: ["**"], write: ["**"], deny: []}}
        """,
    )
    with pytest.raises(ConfigError, match="duplicate"):
        load_config(path)


def test_bad_glob_refuses_boot(tmp_path, vault):
    path = write_config(
        tmp_path,
        f"""\
        vault_root: {vault}
        audit_dir: {tmp_path / 'audit'}
        clients:
          - {{name: a, token_hash_env: T_A, role: admin}}
        roles:
          admin: {{read: ["[unclosed"], write: ["**"], deny: []}}
        """,
    )
    with pytest.raises(ConfigError, match="glob"):
        load_config(path)


def test_missing_required_key_refuses_boot(tmp_path):
    path = write_config(
        tmp_path,
        """\
        clients: []
        roles: {}
        """,
    )
    with pytest.raises(ConfigError):
        load_config(path)


def test_no_clients_refuses_boot(tmp_path, vault):
    path = write_config(
        tmp_path,
        f"""\
        vault_root: {vault}
        audit_dir: {tmp_path / 'audit'}
        clients: []
        roles:
          admin: {{read: ["**"], write: ["**"], deny: []}}
        """,
    )
    with pytest.raises(ConfigError, match="client"):
        load_config(path)


def test_zero_admin_clients_refuses_boot(tmp_path, vault):
    path = write_config(
        tmp_path,
        f"""\
        vault_root: {vault}
        audit_dir: {tmp_path / 'audit'}
        clients:
          - {{name: a, token_hash_env: T_A, role: worker}}
        roles:
          admin: {{read: ["**"], write: ["**"], deny: []}}
          worker: {{read: ["**"], write: [], deny: []}}
        """,
    )
    with pytest.raises(ConfigError, match="admin"):
        load_config(path)


def test_multiple_admin_clients_refuses_boot(tmp_path, vault):
    path = write_config(
        tmp_path,
        f"""\
        vault_root: {vault}
        audit_dir: {tmp_path / 'audit'}
        clients:
          - {{name: a, token_hash_env: T_A, role: admin}}
          - {{name: b, token_hash_env: T_B, role: admin}}
        roles:
          admin: {{read: ["**"], write: ["**"], deny: []}}
        """,
    )
    with pytest.raises(ConfigError, match="admin"):
        load_config(path)


def test_missing_file_refuses_boot(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "does-not-exist.yaml")
