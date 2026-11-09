"""Fixed-window and sliding-window rate limits in Redis.

Both functions take the current time (`now`, seconds since the epoch, float) as an argument
so that tests control the clock. Reads REDIS_URL from the environment.
"""

import os
import uuid

import redis

LIMIT = 10
WINDOW = 60  # seconds

r = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)


# Fixed window (the exercise's allow_request with the clock as an argument) ---------------


def fixed_key(customer_id: int, now: float) -> str:
    return f"ratelimit:fixed:{customer_id}:{int(now // WINDOW)}"


def allow_request_fixed(customer_id: int, now: float) -> bool:
    """10 requests per calendar minute: one INCR counter per customer per minute."""
    key = fixed_key(customer_id, now)
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, WINDOW * 2, nx=True)
    count, _ = pipe.execute()
    return count <= LIMIT


# Sliding window -------------------------------------------------------------------------

# KEYS[1] sorted set of accepted requests (score = request time)
# ARGV[1] now, ARGV[2] window in seconds, ARGV[3] limit, ARGV[4] unique member
# Remove, count and add run inside one script, so no other command runs in between.
_SLIDING_LUA = r.register_script(
    """
    local key    = KEYS[1]
    local now    = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local limit  = tonumber(ARGV[3])

    -- the window is (now - window, now]: drop everything at or before now - window
    redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)

    if redis.call('ZCARD', key) < limit then
        redis.call('ZADD', key, now, ARGV[4])
        redis.call('PEXPIRE', key, math.ceil(window * 1000))
        return 1
    end
    return 0
    """
)


def sliding_key(customer_id: int) -> str:
    return f"ratelimit:sliding:{customer_id}"


def allow_request_sliding(customer_id: int, now: float) -> bool:
    """10 requests in any 60-second window, in a sorted set with the request time as score."""
    # the time alone is not unique (two requests at the same instant would be one member),
    # so the member is the time plus a random UUID
    member = f"{now!r}:{uuid.uuid4().hex}"
    accepted = _SLIDING_LUA(keys=[sliding_key(customer_id)], args=[repr(now), WINDOW, LIMIT, member])
    return accepted == 1
