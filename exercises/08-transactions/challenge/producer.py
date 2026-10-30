"""Inserts jobs into the queue.

Usage:
    uv run python producer.py               10,000 jobs with payload {"n": 1..10000}
    uv run python producer.py --count 500   500 jobs
    uv run python producer.py --slow 30     one job whose processing sleeps 30 s

The connection uses the libpq environment variables (PGHOST, PGUSER,
PGPASSWORD, ...) and the database in PGDATABASE (default: ch08).
"""

import argparse
import os

import psycopg
from psycopg.types.json import Jsonb

DBNAME = os.environ.get("PGDATABASE", "ch08")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10_000)
    parser.add_argument("--slow", type=int, metavar="SECONDS", help="insert one slow job instead")
    args = parser.parse_args()

    with psycopg.connect(dbname=DBNAME) as conn:
        if args.slow:
            (n,) = conn.execute("SELECT coalesce(max(job_id), 0) + 1 FROM job").fetchone()
            job_id = conn.execute(
                "INSERT INTO job (payload) VALUES (%s) RETURNING job_id",
                (Jsonb({"n": n, "sleep": args.slow}),),
            ).fetchone()[0]
            print(f"Inserted slow job {job_id} (sleeps {args.slow} s)")
            return

        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO job (payload) VALUES (%s)",
                [(Jsonb({"n": n}),) for n in range(1, args.count + 1)],
            )
    print(f"Inserted {args.count} jobs")


if __name__ == "__main__":
    main()
