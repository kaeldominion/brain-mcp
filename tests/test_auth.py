import pytest

from brain_mcp.auth import AuthError, TokenRegistry, generate_token, hash_token, token_prefix
from tests.conftest import TOKEN_ENV, TOKENS


@pytest.fixture
def registry(config):
    return TokenRegistry.from_config(config, TOKEN_ENV)


def test_valid_token_authenticates(registry):
    client = registry.authenticate(f"Bearer {TOKENS['management']}")
    assert client.name == "management"
    assert client.role == "admin"


def test_each_client_maps_to_own_identity(registry):
    assert registry.authenticate(f"Bearer {TOKENS['operations']}").name == "operations"
    assert registry.authenticate(f"Bearer {TOKENS['staff']}").name == "staff"


def test_missing_header_rejected(registry):
    with pytest.raises(AuthError):
        registry.authenticate(None)
    with pytest.raises(AuthError):
        registry.authenticate("")


def test_invalid_token_rejected(registry):
    with pytest.raises(AuthError):
        registry.authenticate("Bearer wrong_token_entirely")


def test_non_bearer_scheme_rejected(registry):
    with pytest.raises(AuthError):
        registry.authenticate(f"Basic {TOKENS['management']}")


def test_missing_hash_env_refuses_boot(config):
    env = dict(TOKEN_ENV)
    del env["MCP_TOKEN_HASH_STAFF"]
    with pytest.raises(Exception, match="MCP_TOKEN_HASH_STAFF"):
        TokenRegistry.from_config(config, env)


def test_malformed_hash_env_refuses_boot(config):
    env = dict(TOKEN_ENV)
    env["MCP_TOKEN_HASH_STAFF"] = "not-a-sha256-hash"
    with pytest.raises(Exception, match="MCP_TOKEN_HASH_STAFF"):
        TokenRegistry.from_config(config, env)


def test_generate_token_roundtrip():
    token = generate_token("nnova", "mgmt")
    assert token.startswith("nnova_mgmt_")
    assert len(token) >= len("nnova_mgmt_") + 32
    assert len(hash_token(token)) == 64


def test_token_prefix_reveals_no_secret():
    token = generate_token("nnova", "mgmt")
    prefix = token_prefix(token)
    assert prefix.startswith("nnova_mgmt_")
    # only a short identifying prefix, never the random part
    assert len(prefix) <= len("nnova_mgmt_") + 4
    assert token != prefix
