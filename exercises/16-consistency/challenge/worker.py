"""Apply outbox rows to Redis: add the film's categories to customer:{customer_id}:categories.

Usage: uv run --env-file .env python worker.py [--batch 50] [--pause SECONDS] [--exit-when-idle SECONDS]

Each loop is one PostgreSQL transaction:
  1. claim up to 50 unprocessed rows with FOR UPDATE SKIP LOCKED,
  2. SADD the categories of each film to the customer's set (one Redis pipeline),
  3. set processed_at and COMMIT.
If the worker dies or Redis fails before the COMMIT, the transaction is rolled back, the
rows stay unprocessed and are claimed again. Redis may then receive the same SADD twice,
which changes nothing.
"""

import argparse
import os
import time
from datetime import datetime

import psycopg
import redis

CLAIM_SQL = """
SELECT outbox_id, customer_id, film_id
FROM outbox
WHERE processed_at IS NULL
ORDER BY outbox_id
LIMIT %s
FOR UPDATE SKIP LOCKED
"""

CATEGORIES_SQL = """
SELECT fc.film_id, c.name
FROM film_category fc
JOIN category c ON c.category_id = fc.category_id
WHERE fc.film_id = ANY(%s)
"""


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S.%f}"[:-3] + f"] worker {os.getpid()}: {msg}", flush=True)


def process_batch(conn: psycopg.Connection, r: redis.Redis, size: int, pause: float) -> int:
    """Process one batch in one transaction. Returns the number of rows processed."""
    with conn.transaction():
        rows = conn.execute(CLAIM_SQL, (size,)).fetchall()
        if not rows:
            return 0
        first, last = rows[0][0], rows[-1][0]
        log(f"claimed {len(rows)} rows {first}..{last}")

        film_ids = list({film_id for _, _, film_id in rows})
        categories: dict[int, list[str]] = {}
        for film_id, name in conn.execute(CATEGORIES_SQL, (film_ids,)):
            categories.setdefault(film_id, []).append(name)

        pipe = r.pipeline(transaction=False)
        for _, customer_id, film_id in rows:
            if names := categories.get(film_id):  # a film may have no category
                pipe.sadd(f"customer:{customer_id}:categories", *names)
        pipe.execute()  # raises if Redis is down: the transaction rolls back
        log(f"redis updated for {first}..{last}")

        if pause:  # a window to kill the worker or Redis between Redis and the COMMIT
            time.sleep(pause)

        conn.execute(
            "UPDATE outbox SET processed_at = now() WHERE outbox_id = ANY(%s)",
            ([outbox_id for outbox_id, _, _ in rows],),
        )
    log(f"committed {first}..{last}")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=50)
    parser.add_argument("--pause", type=float, default=0.0, help="seconds between Redis and COMMIT")
    parser.add_argument("--exit-when-idle", type=float, default=0.0,
                        help="stop after this many seconds with nothing to do (0: run forever)")
    args = parser.parse_args()

    r = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    log("started")
    idle_since = None
    backoff = 0.5

    while True:
        try:
            n = process_batch(conn, r, args.batch, args.pause)
            backoff = 0.5
        except redis.RedisError as e:
            # the transaction was rolled back: the rows are unprocessed again
            log(f"redis error, batch rolled back: {e.__class__.__name__}: {e}; retry in {backoff} s")
            time.sleep(backoff)
            backoff = min(backoff * 2, 5)
            continue

        if n:
            idle_since = None
            continue
        idle_since = idle_since or time.monotonic()
        if args.exit_when_idle and time.monotonic() - idle_since >= args.exit_when_idle:
            left = conn.execute("SELECT count(*) FROM outbox WHERE processed_at IS NULL").fetchone()[0]
            conn.commit()
            log(f"idle for {args.exit_when_idle} s, {left} unprocessed rows left, exiting")
            return
        time.sleep(0.2)


if __name__ == "__main__":
    main()
