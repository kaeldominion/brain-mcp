import pytest

from brain_mcp.errors import RateLimited
from brain_mcp.ratelimit import RateLimiter


def test_allows_up_to_limit():
    rl = RateLimiter(requests_per_minute=5)
    for _ in range(5):
        rl.check("client-a", now=100.0)


def test_blocks_over_limit_with_structured_error():
    rl = RateLimiter(requests_per_minute=3)
    for _ in range(3):
        rl.check("client-a", now=100.0)
    with pytest.raises(RateLimited) as exc:
        rl.check("client-a", now=100.5)
    assert exc.value.data.get("retry_after_seconds") is not None


def test_limits_are_per_client():
    rl = RateLimiter(requests_per_minute=2)
    rl.check("a", now=10.0)
    rl.check("a", now=10.0)
    rl.check("b", now=10.0)  # unaffected by a's usage
    with pytest.raises(RateLimited):
        rl.check("a", now=10.0)


def test_window_slides():
    rl = RateLimiter(requests_per_minute=2)
    rl.check("a", now=0.0)
    rl.check("a", now=1.0)
    with pytest.raises(RateLimited):
        rl.check("a", now=2.0)
    rl.check("a", now=61.0)  # first request aged out
