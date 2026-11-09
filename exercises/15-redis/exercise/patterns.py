"""Four Redis patterns on Pagila data.

Reads DATABASE_URL (PostgreSQL, database ex15) and REDIS_URL from the environment.
"""

import json
import os
import secrets
import time
from decimal import Decimal

import psycopg
import redis

r = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)


def pg_connect() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


# 1. Recently viewed films ---------------------------------------------------

VIEWED_MAX = 20
VIEWED_TTL = 30 * 24 * 3600  # 30 days = 2,592,000 s


def viewed_key(customer_id: int) -> str:
    return f"customer:{customer_id}:viewed"


def record_view(customer_id: int, film_id: int) -> None:
    """Add the film with the current time as score, keep the 20 most recent, renew the TTL."""
    key = viewed_key(customer_id)
    pipe = r.pipeline()  # MULTI/EXEC: the three commands run as one unit
    pipe.zadd(key, {str(film_id): time.time()})  # same member -> score updated, no duplicate
    pipe.zremrangebyrank(key, 0, -(VIEWED_MAX + 1))  # drop everything but the top 20 scores
    pipe.expire(key, VIEWED_TTL)
    pipe.execute()


def recent_views(customer_id: int) -> list[int]:
    """Film IDs, most recent first."""
    return [int(f) for f in r.zrange(viewed_key(customer_id), 0, -1, desc=True)]


# 2. Cache-aside -------------------------------------------------------------

FILM_CACHE_TTL = 300


def film_cache_key(film_id: int) -> str:
    return f"cache:film:{film_id}"


def get_film(film_id: int) -> dict | None:
    """Read from Redis; on a miss read PostgreSQL and cache the result for 300 s."""
    key = film_cache_key(film_id)
    cached = r.get(key)
    if cached is not None:
        film = json.loads(cached)
        film["rental_rate"] = Decimal(film["rental_rate"])
        return film

    with pg_connect() as conn:
        row = conn.execute(
            "SELECT title, rating::text, length, rental_rate FROM film WHERE film_id = %s",
            (film_id,),
        ).fetchone()
    if row is None:
        return None
    title, rating, length, rental_rate = row
    film = {"title": title, "rating": rating, "length": length, "rental_rate": rental_rate}
    # Decimal is stored as a string so 0.99 stays exactly 0.99
    r.set(key, json.dumps({**film, "rental_rate": str(rental_rate)}), ex=FILM_CACHE_TTL)
    return film


def update_film_rate(film_id: int, rate: Decimal | float | str) -> None:
    """Update PostgreSQL first, then invalidate the cache (the next read repopulates it)."""
    with pg_connect() as conn:
        conn.execute(
            "UPDATE film SET rental_rate = %s WHERE film_id = %s", (Decimal(str(rate)), film_id)
        )
    # the connection context manager committed; only now delete the cached copy
    r.delete(film_cache_key(film_id))


# 3. Lock --------------------------------------------------------------------

# Delete the key only if it still holds our token: GET + DEL in one atomic step.
_RELEASE_LUA = r.register_script(
    """
    if redis.call('GET', KEYS[1]) == ARGV[1] then
        return redis.call('DEL', KEYS[1])
    else
        return 0
    end
    """
)


def acquire_lock(name: str, ttl: int = 60) -> str | None:
    """SET lock NX EX ttl with a random token. Returns the token, or None if the lock is held."""
    token = secrets.token_hex(16)
    if r.set(name, token, nx=True, ex=ttl):
        return token
    return None


def release_lock(name: str, token: str) -> bool:
    """True if the lock was ours and was deleted; False if it is held by someone else (or expired)."""
    return _RELEASE_LUA(keys=[name], args=[token]) == 1


# 4. Rate limit (fixed window) -----------------------------------------------

RATE_LIMIT = 10
RATE_WINDOW = 60


def rate_key(customer_id: int, window: int) -> str:
    return f"ratelimit:{customer_id}:{window}"


def allow_request(customer_id: int) -> bool:
    """10 requests per customer per calendar minute; one counter per minute that expires."""
    window = int(time.time()) // RATE_WINDOW  # minute number since the epoch
    key = rate_key(customer_id, window)
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, RATE_WINDOW * 2, nx=True)  # set once; 2 min covers clock skew at the edge
    count, _ = pipe.execute()
    return count <= RATE_LIMIT
