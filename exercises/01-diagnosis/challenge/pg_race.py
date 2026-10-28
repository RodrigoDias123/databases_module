"""10 processes insert 1,000 records each into the same PostgreSQL table.

Create the database first, from the repository root:
    ./scripts/create-db.sh ch01

Run from this folder:
    uv run pg_race.py
"""

import os
from multiprocessing import Process

import psycopg

WORKERS = 10
RECORDS_PER_WORKER = 1_000

DSN = os.environ.get(
    "DATABASE_URL",
    f"host={os.environ.get('PGHOST', 'localhost')} dbname=ch01",
)


def worker(worker_id: int) -> None:
    # Each process has its own connection, and each INSERT commits on its own.
    with psycopg.connect(DSN, autocommit=True) as conn:
        for n in range(RECORDS_PER_WORKER):
            conn.execute(
                "INSERT INTO record (worker, n) VALUES (%s, %s)",
                (worker_id, n),
            )


def main() -> None:
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS record (worker integer NOT NULL, n integer NOT NULL)"
        )
        conn.execute("TRUNCATE record")

    procs = [Process(target=worker, args=(w,)) for w in range(WORKERS)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()

    with psycopg.connect(DSN) as conn:
        count = conn.execute("SELECT count(*) FROM record").fetchone()[0]
    print(f"SELECT count(*) FROM record: {count} / {WORKERS * RECORDS_PER_WORKER}")


if __name__ == "__main__":
    main()
