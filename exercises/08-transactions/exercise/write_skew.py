"""Write skew: 20 staff members of store 1 each try to deactivate themselves.

Rule: every store keeps at least one active staff member.
Each thread counts the active staff of store 1 and, if the count is above 1,
deactivates its own member. A barrier between the count and the update makes
every thread read before any thread writes.

Usage:
    uv run python write_skew.py read-committed
    uv run python write_skew.py serializable

The connection uses the libpq environment variables (PGHOST, PGUSER,
PGPASSWORD, ...) and the database in PGDATABASE (default: ex08).
"""

import os
import sys
import threading

import psycopg
from psycopg import IsolationLevel
from psycopg.errors import SerializationFailure

STORE_ID = 1
THREADS = 20
DBNAME = os.environ.get("PGDATABASE", "ex08")

LEVELS = {
    "read-committed": IsolationLevel.READ_COMMITTED,
    "serializable": IsolationLevel.SERIALIZABLE,
}

COUNT_ACTIVE = "SELECT count(*) FROM staff WHERE store_id = %s AND active"
DEACTIVATE = "UPDATE staff SET active = false WHERE staff_id = %s"

print_lock = threading.Lock()


def log(message):
    with print_lock:
        print(message, flush=True)


def active_staff_ids():
    with psycopg.connect(dbname=DBNAME) as conn:
        rows = conn.execute(
            "SELECT staff_id FROM staff WHERE store_id = %s AND active ORDER BY staff_id",
            (STORE_ID,),
        ).fetchall()
    return [row[0] for row in rows]


def worker(staff_id, level, barrier, results):
    with psycopg.connect(dbname=DBNAME) as conn:
        conn.isolation_level = level
        attempt = 0
        while True:
            attempt += 1
            try:
                with conn.transaction():
                    count = conn.execute(COUNT_ACTIVE, (STORE_ID,)).fetchone()[0]
                    # Only the first attempt waits: every thread reads before any thread writes.
                    if attempt == 1:
                        barrier.wait()
                    if count > 1:
                        conn.execute(DEACTIVATE, (staff_id,))
                        outcome = "deactivated"
                    else:
                        outcome = "stayed active"
                log(f"staff {staff_id:>3}  attempt {attempt}  saw {count:>2} active  -> {outcome}")
                results[staff_id] = (outcome, attempt)
                return
            except SerializationFailure as e:
                log(f"staff {staff_id:>3}  attempt {attempt}  40001 serialization failure, retrying ({e.diag.message_detail})")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in LEVELS:
        sys.exit(f"Usage: {sys.argv[0]} {{{' | '.join(LEVELS)}}}")
    level = LEVELS[sys.argv[1]]

    staff_ids = active_staff_ids()
    if len(staff_ids) != THREADS:
        sys.exit(
            f"Store {STORE_ID} has {len(staff_ids)} active staff, expected {THREADS}. "
            f"Reset with: UPDATE staff SET active = true WHERE store_id = {STORE_ID};"
        )

    print(f"Isolation level: {level.name}, {THREADS} threads, {len(staff_ids)} active before")
    barrier = threading.Barrier(THREADS, timeout=10)
    results = {}
    threads = [
        threading.Thread(target=worker, args=(staff_id, level, barrier, results))
        for staff_id in staff_ids
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    deactivated = sum(1 for outcome, _ in results.values() if outcome == "deactivated")
    retries = sum(attempt - 1 for _, attempt in results.values())
    remaining = len(active_staff_ids())
    print(f"Deactivated: {deactivated}, retries: {retries}")
    print(f"Active staff in store {STORE_ID} afterwards: {remaining}")
    print("RULE BROKEN" if remaining < 1 else "OK: rule kept")


if __name__ == "__main__":
    main()
