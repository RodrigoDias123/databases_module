import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from rate_limit import (
    LIMIT,
    allow_request_fixed,
    allow_request_sliding,
    fixed_key,
    r,
    sliding_key,
)

CUSTOMER = 900_001  # an ID outside Pagila so the tests do not touch real keys
MINUTE = 1_800_000_000 - 1_800_000_000 % 60  # start of a minute (epoch seconds)


@pytest.fixture(autouse=True)
def clean_keys():
    def clean():
        keys = list(r.scan_iter(f"ratelimit:*:{CUSTOMER}*"))
        if keys:
            r.delete(*keys)

    clean()
    yield
    clean()


def burst_at_minute_boundary() -> list[float]:
    """10 requests at seconds 59.0..59.9 of one minute, 10 at 0.0..0.9 of the next."""
    end_of_minute = [MINUTE + 59 + i / 10 for i in range(10)]
    start_of_next = [MINUTE + 60 + i / 10 for i in range(10)]
    return end_of_minute + start_of_next


def test_fixed_window_accepts_20_sliding_accepts_10_at_minute_boundary():
    times = burst_at_minute_boundary()

    fixed = [allow_request_fixed(CUSTOMER, t) for t in times]
    sliding = [allow_request_sliding(CUSTOMER, t) for t in times]

    print(f"\nfixed:   {sum(fixed)} accepted -> {fixed}")
    print(f"sliding: {sum(sliding)} accepted -> {sliding}")

    # the fixed window resets at second 0.0, so the 20 requests in 1.9 s all pass
    assert fixed == [True] * 20
    assert r.get(fixed_key(CUSTOMER, MINUTE + 59)) == "10"
    assert r.get(fixed_key(CUSTOMER, MINUTE + 60)) == "10"
    # the sliding window still sees the 10 requests from 59.x, so the next 10 are rejected
    assert sliding == [True] * 10 + [False] * 10
    assert r.zcard(sliding_key(CUSTOMER)) == 10


def test_sliding_window_accepts_again_after_60_seconds():
    for i in range(10):
        assert allow_request_sliding(CUSTOMER, MINUTE + i)  # seconds 0..9
    assert not allow_request_sliding(CUSTOMER, MINUTE + 59.9)
    # at second 60 the request from second 0 leaves the window (60 s old), one slot frees up
    assert allow_request_sliding(CUSTOMER, MINUTE + 60)
    assert not allow_request_sliding(CUSTOMER, MINUTE + 60.5)


def test_sliding_window_exactly_10_of_30_concurrent_requests():
    now = MINUTE + 30.0  # every request at the same moment, so every score is the same
    threads, per_thread = 10, 3
    start = threading.Barrier(threads)

    def worker() -> list[bool]:
        start.wait()  # release the 10 threads together
        return [allow_request_sliding(CUSTOMER, now) for _ in range(per_thread)]

    with ThreadPoolExecutor(max_workers=threads) as pool:
        futures = [pool.submit(worker) for _ in range(threads)]
        results = [ok for f in futures for ok in f.result()]

    print(f"\n{len(results)} requests, {sum(results)} accepted, {results.count(False)} rejected")

    assert len(results) == 30
    assert sum(results) == LIMIT
    # 10 members although all scores are equal: each member is unique
    assert r.zcard(sliding_key(CUSTOMER)) == LIMIT
