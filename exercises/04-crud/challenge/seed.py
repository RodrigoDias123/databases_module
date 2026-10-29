"""Adds 1,000,000 rentals to a copy of Pagila with COPY.

Run from this folder:
    uv run seed.py ch04_a
"""

import os
import sys
import time
from datetime import UTC, datetime, timedelta

import psycopg
from faker import Faker

ROWS = 1_000_000
FIRST_ID = 100_001
LAST_ID = FIRST_ID + ROWS - 1
SEED = 42
BATCH = 50_000

# Row i gets a rental_date inside its own 144-second slot, so every new
# rental_date is later than the previous one and the unique index
# (rental_date, inventory_id, customer_id) can never be violated by two new rows.
# 1,000,000 slots of 144 s go from 2022-01-01 to 2026-07-25.
START = datetime(2022, 1, 1, tzinfo=UTC)
SLOT_MICROSECONDS = 144_000_000
NOT_RETURNED_PERCENT = 2
LAST_UPDATE = "2026-01-01 00:00:00+00"

CHECKSUM = """
    SELECT count(*),
           md5(string_agg(concat_ws('|', rental_id, rental_date, inventory_id, customer_id, return_date, staff_id), ','
                          ORDER BY rental_id))
    FROM rental WHERE rental_id > 100000
"""


def ids(cur: psycopg.Cursor, table: str, column: str) -> list[int]:
    """All ids of a table, ordered, so the same database gives the same list."""
    cur.execute(f"SELECT {column} FROM {table} ORDER BY {column}")
    return [row[0] for row in cur.fetchall()]


def generate(inventory: list[int], customers: list[int], staff: list[int], taken: set):
    """Yields COPY text lines, the same ones on every run."""
    Faker.seed(SEED)
    fake = Faker()

    def pick(values: list[int]) -> int:
        # random_int on the index is ~9x faster than fake.random_element(values).
        return values[fake.random_int(0, len(values) - 1)]

    slot = timedelta(microseconds=SLOT_MICROSECONDS)
    for i in range(ROWS):
        slot_start = START + i * slot
        rental_date = fake.date_time_between(slot_start, slot_start + slot - timedelta(microseconds=1), tzinfo=UTC)
        inventory_id, customer_id = pick(inventory), pick(customers)
        # The original Pagila rentals share the same dates; never repeat one of their keys.
        while (rental_date, inventory_id, customer_id) in taken:
            inventory_id, customer_id = pick(inventory), pick(customers)
        if fake.boolean(chance_of_getting_true=NOT_RETURNED_PERCENT):
            return_date = r"\N"
        else:
            # Between 1 hour and 10 days later, always after rental_date.
            return_date = fake.date_time_between(
                rental_date + timedelta(hours=1), rental_date + timedelta(days=10), tzinfo=UTC
            ).isoformat()
        yield (
            f"{FIRST_ID + i}\t{rental_date.isoformat()}\t{inventory_id}\t{customer_id}\t"
            f"{return_date}\t{pick(staff)}\t{LAST_UPDATE}\t{fake.uuid4()}\n"
        )


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: uv run seed.py <database>")
    dbname = sys.argv[1]
    started = time.perf_counter()

    # DATABASE_URL (from .env) gives the host and password; the database is the argument.
    with psycopg.connect(os.environ.get("DATABASE_URL", ""), dbname=dbname) as conn, conn.cursor() as cur:
        cur.execute(CHECKSUM)
        print(f"{dbname}: before: %s rows, md5 %s" % cur.fetchone())

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
            cur.execute("SELECT rental_date, inventory_id, customer_id FROM rental")
            taken = set(cur.fetchall())

            with cur.copy(
                "COPY rental (rental_id, rental_date, inventory_id, customer_id,"
                " return_date, staff_id, last_update, uuid) FROM STDIN"
            ) as copy:
                batch = []
                for line in generate(inventory, customers, staff, taken):
                    batch.append(line)
                    if len(batch) == BATCH:
                        copy.write("".join(batch))
                        batch.clear()
                copy.write("".join(batch))
            print(f"{dbname}: inserted {cur.rowcount:,} rentals")

        # The ids were given explicitly, so the sequence has to move past them.
        cur.execute("SELECT setval('rental_rental_id_seq', (SELECT max(rental_id) FROM rental))")
        conn.commit()

        cur.execute(CHECKSUM)
        print(f"{dbname}: after:  %s rows, md5 %s" % cur.fetchone())

    print(f"{dbname}: {time.perf_counter() - started:.1f} s")


if __name__ == "__main__":
    main()
