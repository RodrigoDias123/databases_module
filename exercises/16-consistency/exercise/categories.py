"""Shared pieces of rebuild.py and verify.py: connections, key names and the one query.

Reads DATABASE_URL (PostgreSQL, database ex16) and REDIS_URL (Redis database 1).
"""

import os
from collections import defaultdict

import psycopg
import redis

r = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)

KEY_PATTERN = "customer:*:categories"

# Every (customer, category) pair of every film the customer has rented. A film with
# several categories gives several rows; DISTINCT removes repeated rentals of a category.
CATEGORIES_SQL = """
SELECT DISTINCT r.customer_id, c.name
FROM rental r
JOIN inventory i      ON i.inventory_id = r.inventory_id
JOIN film_category fc ON fc.film_id = i.film_id
JOIN category c       ON c.category_id = fc.category_id
ORDER BY r.customer_id, c.name
"""


def categories_key(customer_id: int) -> str:
    return f"customer:{customer_id}:categories"


def expected_sets() -> dict[str, set[str]]:
    """{key: category names} for every customer with rentals, from one PostgreSQL query."""
    expected: dict[str, set[str]] = defaultdict(set)
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        for customer_id, name in conn.execute(CATEGORIES_SQL):
            expected[categories_key(customer_id)].add(name)
    return dict(expected)


def existing_keys() -> set[str]:
    """Every customer:*:categories key in Redis, found with SCAN (KEYS would block Redis)."""
    return set(r.scan_iter(match=KEY_PATTERN, count=1000))
