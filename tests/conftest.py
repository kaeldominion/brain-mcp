import hashlib
import textwrap

import pytest

VALID_CONFIG = """\
vault_root: {vault_root}
audit_dir: {audit_dir}
clients:
  - name: management
    token_hash_env: MCP_TOKEN_HASH_MANAGEMENT
    role: admin
  - name: operations
    token_hash_env: MCP_TOKEN_HASH_OPERATIONS
    role: operations
  - name: staff
    token_hash_env: MCP_TOKEN_HASH_STAFF
    role: staff
roles:
  admin:
    read:  ["**"]
    write: ["**"]
    deny:  ["_Audit/**", "_System/Access and Contribution Rules.md", ".obsidian/**"]
  operations:
    read:  ["40 Properties/**", "50 Operations/**", "70 Meetings/**", "20 People/**", "30 Projects/**", "_System/**"]
    write: ["40 Properties/**", "50 Operations/**", "70 Meetings/**", "90 Staff Inbox/{{client}}/**"]
    deny:  ["_Audit/**", ".obsidian/**"]
  staff:
    read:  ["50 Operations/Procedures/**", "40 Properties/**", "_System/**"]
    write: ["90 Staff Inbox/{{client}}/**"]
    deny:  ["_Audit/**", ".obsidian/**"]
limits:
  requests_per_minute: 60
  max_note_bytes: 1048576
"""

TOKENS = {
    "management": "test_mgmt_0123456789abcdef0123456789abcdef",
    "operations": "test_ops_0123456789abcdef0123456789abcdef",
    "staff": "test_staff_0123456789abcdef0123456789abcdef",
}


def sha256(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


TOKEN_ENV = {
    "MCP_TOKEN_HASH_MANAGEMENT": sha256(TOKENS["management"]),
    "MCP_TOKEN_HASH_OPERATIONS": sha256(TOKENS["operations"]),
    "MCP_TOKEN_HASH_STAFF": sha256(TOKENS["staff"]),
}


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    for d in [
        "_System/Templates",
        "10 Companies",
        "20 People",
        "40 Properties",
        "50 Operations/Procedures",
        "70 Meetings",
        "80 Decisions",
        "90 Staff Inbox/operations",
        "90 Staff Inbox/staff",
        "_Archive",
    ]:
        (root / d).mkdir(parents=True)
    (root / "_System" / "Company 2nd Brain Home.md").write_text("# Home\n")
    return root


@pytest.fixture
def config_file(tmp_path, vault):
    audit = tmp_path / "audit"
    audit.mkdir()
    path = tmp_path / "brain.config.yaml"
    path.write_text(VALID_CONFIG.format(vault_root=vault, audit_dir=audit))
    return path


@pytest.fixture
def config(config_file):
    from brain_mcp.config import load_config

    return load_config(config_file)


def write_config(tmp_path, body: str):
    path = tmp_path / "bad.config.yaml"
    path.write_text(textwrap.dedent(body))
    return path
