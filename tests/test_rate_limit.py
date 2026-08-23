from app.rate_limit import SlidingWindowLimiter


def test_sliding_window_limiter_blocks_after_limit():
    limiter = SlidingWindowLimiter(2, window_s=60)
    assert limiter.allow("client")[0] is True
    assert limiter.allow("client")[0] is True
    allowed, retry_after = limiter.allow("client")
    assert allowed is False
    assert retry_after >= 1
