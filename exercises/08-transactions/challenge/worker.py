"""Processes jobs from the queue until there are no pending jobs left.

Each job is one transaction: claim it with FOR UPDATE SKIP LOCKED, process it
(sleep 1 to 5 ms, or payload["sleep"] seconds, and insert a row into
job_result), mark it done, commit.

Usage:
    uv run python worker.py <worker number>

The connection uses the libpq environment variables (PGHOST, PGUSER,
PGPASSWORD, ...) and the database in PGDATABASE (default: ch08).
"""

import os
import random
import sys
import time

import psycopg

DBNAME = os.environ.get("PGDATABASE", "ch08")

CLAIM = """
SELECT job_id, payload FROM job
WHERE status = 'pending'
ORDER BY job_id
FOR UPDATE SKIP LOCKED
LIMIT 1
"""


def process(conn, worker, job_id, payload):
    conn.execute("INSERT INTO job_result (job_id, worker) VALUES (%s, %s)", (job_id, worker))
    seconds = payload.get("sleep")
    if seconds:
        print(f"worker {worker}: job {job_id} sleeps {seconds} s", flush=True)
        time.sleep(seconds)
    else:
        time.sleep(random.uniform(0.001, 0.005))


def main():
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} <worker number>")
    worker = int(sys.argv[1])

    processed = 0
    # autocommit: each conn.transaction() block is then a real BEGIN ... COMMIT,
    # not a savepoint inside one long implicit transaction.
    with psycopg.connect(dbname=DBNAME, autocommit=True) as conn:
        backend_pid = conn.execute("SELECT pg_backend_pid()").fetchone()[0]
        print(f"worker {worker}: started, pid {os.getpid()}, backend pid {backend_pid}", flush=True)
        while True:
            with conn.transaction():
                row = conn.execute(CLAIM).fetchone()
                if row is None:
                    break
                job_id, payload = row
                process(conn, worker, job_id, payload)
                conn.execute("UPDATE job SET status = 'done' WHERE job_id = %s", (job_id,))
            processed += 1
    print(f"worker {worker}: no pending jobs, processed {processed}", flush=True)


if __name__ == "__main__":
    main()
