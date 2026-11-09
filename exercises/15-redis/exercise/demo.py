"""Demonstrates the four patterns of patterns.py step by step."""

import time
from decimal import Decimal

from patterns import (
    acquire_lock,
    allow_request,
    film_cache_key,
    get_film,
    r,
    rate_key,
    record_view,
    recent_views,
    release_lock,
    update_film_rate,
    viewed_key,
)


def title(text: str) -> None:
    print(f"\n=== {text} ===")


def recently_viewed() -> None:
    title("1. Recently viewed films (sorted set)")
    r.delete(viewed_key(1))
    for film_id in range(1, 26):
        record_view(1, film_id)
    print("customer 1 viewed films 1..25 in order")
    views = recent_views(1)
    print(f"recent_views(1) -> {views}")
    print(f"  {len(views)} films, expected 25 down to 6: {views == list(range(25, 5, -1))}")

    record_view(1, 10)
    views = recent_views(1)
    print("customer 1 viewed film 10 again")
    print(f"recent_views(1) -> {views}")
    print(f"  film 10 first: {views[0] == 10}, appears once: {views.count(10) == 1}, size {len(views)}")
    print(f"TTL {viewed_key(1)} -> {r.ttl(viewed_key(1))} s (30 days = 2592000)")


def cache_aside() -> None:
    title("2. Cache-aside (film details)")
    key = film_cache_key(1)
    # start from a known state so the demo can be re-run
    update_film_rate(1, Decimal("0.99"))
    print(f"setup: film 1 rental_rate = 0.99 in PostgreSQL, {key} deleted")

    def show() -> None:
        hit = r.exists(key) == 1
        film = get_film(1)
        print(f"get_film(1) -> {'HIT ' if hit else 'MISS'} {film} | TTL {r.ttl(key)} s")

    show()
    show()
    update_film_rate(1, 1.99)
    print(f"update_film_rate(1, 1.99) -> {key} exists: {r.exists(key) == 1}")
    show()


def lock() -> None:
    title("3. Lock (token + Lua release)")
    name = "lock:demo"
    r.delete(name)
    token_a = acquire_lock(name, 60)
    print(f"A acquire_lock -> token {token_a[:8]}...")
    token_b = acquire_lock(name, 60)
    print(f"B acquire_lock -> {token_b} (held by A)")
    print(f"B release_lock with a wrong token -> {release_lock(name, 'not-the-token')}, "
          f"lock still there: {r.exists(name) == 1}")
    print(f"A release_lock with its token     -> {release_lock(name, token_a)}, "
          f"lock still there: {r.exists(name) == 1}")
    print("(two real processes: see refresh.py)")


def rate_limit() -> None:
    title("4. Rate limit (10 per customer per minute)")
    # wait if we are too close to the end of a minute, so the 12 calls land in the same window
    if time.time() % 60 > 55:
        time.sleep(60 - time.time() % 60 + 0.1)
    window = int(time.time()) // 60
    r.delete(rate_key(1, window))
    results = [allow_request(1) for _ in range(12)]
    print(f"12 calls -> {results}")
    print(f"  True: {results.count(True)}, False: {results.count(False)}")
    key = rate_key(1, window)
    print(f"  {key} = {r.get(key)}, TTL {r.ttl(key)} s")

    wait = 60 - time.time() % 60 + 0.1
    print(f"waiting {wait:.1f} s for the next minute...")
    time.sleep(wait)
    new_key = rate_key(1, int(time.time()) // 60)
    print(f"next minute: allow_request(1) -> {allow_request(1)} ({new_key} = {r.get(new_key)})")


if __name__ == "__main__":
    recently_viewed()
    cache_aside()
    lock()
    rate_limit()
