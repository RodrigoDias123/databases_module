"""Adds 1,000,000 rentals to a copy of Pagila with COPY.

Run from this folder:
    uv run seed.py ex04_a
"""

import os
import random
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta

import psycopg

ROWS = 1_000_000
FIRST_ID = 1_000_001
LAST_ID = FIRST_ID + ROWS - 1
SEED = 42
BATCH = 50_000

# Every row gets a rental_date later than the previous one, so the unique index
# (rental_date, inventory_id, customer_id) can never be violated.
START = datetime(2022, 3, 1, tzinfo=UTC)
STEP_SECONDS = 120
LAST_UPDATE = "2026-01-01 00:00:00+00"

FINGERPRINT = f"""
    SELECT md5(string_agg(r::text, ',' ORDER BY rental_id))
    FROM rental r
    WHERE rental_id BETWEEN {FIRST_ID} AND {LAST_ID}
"""


def ids(cur: psycopg.Cursor, table: str, column: str) -> list[int]:
    """All ids of a table, ordered, so the same database gives the same list."""
    cur.execute(f"SELECT {column} FROM {table} ORDER BY {column}")
    return [row[0] for row in cur.fetchall()]


def generate(inventory: list[int], customers: list[int], staff: list[int]):
    """Yields COPY text lines, the same ones on every run."""
    rng = random.Random(SEED)
    for i in range(ROWS):
        rental_date = START + timedelta(seconds=i * STEP_SECONDS + rng.randrange(STEP_SECONDS))
        # Between 1 hour and 10 days later, always after rental_date.
        return_date = rental_date + timedelta(seconds=rng.randrange(3_600, 10 * 86_400))
        row_uuid = uuid.UUID(bytes=rng.randbytes(16), version=4)
        yield (
            f"{FIRST_ID + i}\t{rental_date.isoformat()}\t{rng.choice(inventory)}\t"
            f"{rng.choice(customers)}\t{return_date.isoformat()}\t{rng.choice(staff)}\t"
            f"{LAST_UPDATE}\t{row_uuid}\n"
        )


def main() -> None:
    dbname = sys.argv[1] if len(sys.argv) > 1 else "ex04"
    dsn = os.environ.get(
        "DATABASE_URL",
        f"host={os.environ.get('PGHOST', 'localhost')} dbname={dbname}",
    )
    started = time.perf_counter()

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        # Two runs at the same time would both see 0 rows; the lock makes the second wait.
        cur.execute("LOCK TABLE rental IN SHARE ROW EXCLUSIVE MODE")
        cur.execute(
            "SELECT count(*) FROM rental WHERE rental_id BETWEEN %s AND %s",
            (FIRST_ID, LAST_ID),
        )
        existing = cur.fetchone()[0]
        if existing == ROWS:
            print(f"{dbname}: the {ROWS:,} rentals are already there, nothing to do")
        elif existing:
            sys.exit(f"{dbname}: {existing:,} rows in the seed range, expected 0 or {ROWS:,}")
        else:
            inventory = ids(cur, "inventory", "inventory_id")
            customers = ids(cur, "customer", "customer_id")
            staff = ids(cur, "staff", "staff_id")

            with cur.copy(
                "COPY rental (rental_id, rental_date, inventory_id, customer_id,"
                " return_date, staff_id, last_update, uuid) FROM STDIN"
            ) as copy:
                batch = []
                for line in generate(inventory, customers, staff):
                    batch.append(line)
                    if len(batch) == BATCH:
                        copy.write("".join(batch))
                        batch.clear()
                copy.write("".join(batch))
            print(f"{dbname}: inserted {cur.rowcount:,} rentals")

        conn.commit()

        cur.execute(FINGERPRINT)
        print(f"{dbname}: md5 of the seeded rows = {cur.fetchone()[0]}")

    print(f"{dbname}: {time.perf_counter() - started:.1f} s")


if __name__ == "__main__":
    main()
