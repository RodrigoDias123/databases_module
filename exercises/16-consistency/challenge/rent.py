"""Insert N rentals for random existing customers and copies, each with its outbox row.

Usage: uv run --env-file .env python rent.py N [--delay SECONDS]

The rental and its outbox row are inserted in the same PostgreSQL transaction: either
both are committed or neither is, so the worker never misses a rental and never sees an
outbox row for a rental that does not exist.
"""

import argparse
import os
import random
import time
from datetime import datetime

import psycopg


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S.%f}"[:-3] + f"] rent: {msg}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("n", type=int, help="number of rentals to insert")
    parser.add_argument("--delay", type=float, default=0.0, help="seconds to wait between rentals")
    args = parser.parse_args()

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        customers = [c for (c,) in conn.execute("SELECT customer_id FROM customer")]
        copies = conn.execute("SELECT inventory_id, film_id, store_id FROM inventory").fetchall()
        staff_ids = [s for (s,) in conn.execute("SELECT staff_id FROM staff")]
        staff_by_store = dict(
            conn.execute("SELECT store_id, array_agg(staff_id) FROM staff GROUP BY store_id")
        )
        conn.commit()

        for done in range(1, args.n + 1):
            customer_id = random.choice(customers)
            inventory_id, film_id, store_id = random.choice(copies)
            # someone from the copy's store; any staff member if that store has none
            staff_id = random.choice(staff_by_store.get(store_id) or staff_ids)
            with conn.transaction():  # BEGIN ... COMMIT around both inserts
                conn.execute(
                    """INSERT INTO rental (rental_date, inventory_id, customer_id, staff_id)
                       VALUES (clock_timestamp(), %s, %s, %s)""",
                    (inventory_id, customer_id, staff_id),
                )
                conn.execute(
                    "INSERT INTO outbox (customer_id, film_id) VALUES (%s, %s)",
                    (customer_id, film_id),
                )
            if done % 500 == 0 or done == args.n:
                log(f"{done}/{args.n} rentals committed")
            if args.delay:
                time.sleep(args.delay)


if __name__ == "__main__":
    main()
