import logging

from brain_mcp.server import RedactionFilter


def _emit(msg, *args):
    record = logging.LogRecord("test", logging.INFO, __file__, 1, msg, args, None)
    RedactionFilter().filter(record)
    return record.getMessage()


def test_bearer_header_redacted():
    out = _emit("request with Authorization: Bearer nnova_mgmt_deadbeefdeadbeefdeadbeef")
    assert "deadbeef" not in out
    assert "[REDACTED]" in out


def test_token_shaped_string_redacted():
    out = _emit("client sent token nnova_mgmt_0123456789abcdef0123456789abcdef in body")
    assert "0123456789abcdef" not in out


def test_normal_messages_untouched():
    msg = "GET /mcp 200 OK for client management"
    assert _emit(msg) == msg


def test_args_are_flattened_safely():
    out = _emit("header=%s", "Bearer nnova_ops_ffffffffffffffffffffffffffffffff")
    assert "ffffffff" not in out
