"""10 concurrent writers, 1,000 records each: a JSON file vs a PostgreSQL table.

Run from this folder:
    uv run race.py
"""

import json
import os
import time
from multiprocessing import Process, Value
from pathlib import Path

import psycopg

WORKERS = 10
RECORDS_PER_WORKER = 1_000
EXPECTED = WORKERS * RECORDS_PER_WORKER
READ_RETRIES = 50

JSON_FILE = Path(__file__).with_name("records.json")
DSN = os.environ.get(
    "DATABASE_URL",
    f"host={os.environ.get('PGHOST', 'localhost')} dbname=ex01_challenge",
)


# --- JSON file: read, append, write back -----------------------------------

def read_records() -> list | None:
    """The file's records, or None if it stays unreadable after every retry."""
    for _ in range(READ_RETRIES):
        try:
            return json.loads(JSON_FILE.read_text())
        except json.JSONDecodeError:
            # Another process may be halfway through rewriting the file.
            time.sleep(0.001)
    return None


def json_worker(worker_id: int, resets) -> None:
    for i in range(RECORDS_PER_WORKER):
        records = read_records()
        if records is None:
            # The file is corrupt for good: start over, losing everything in it.
            with resets.get_lock():
                resets.value += 1
            records = []
        records.append({"worker": worker_id, "seq": i})
        JSON_FILE.write_text(json.dumps(records))


def run_json() -> str:
    JSON_FILE.write_text("[]")
    resets = Value("i", 0)
    procs = [Process(target=json_worker, args=(w, resets)) for w in range(WORKERS)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    records = read_records()
    count = "corrupt" if records is None else len(records)
    return f"{count} / {EXPECTED}  (file corrupt and reset {resets.value} times)"


# --- PostgreSQL: one connection per process --------------------------------

def pg_worker(worker_id: int) -> None:
    with psycopg.connect(DSN, autocommit=True) as conn:
        for i in range(RECORDS_PER_WORKER):
            conn.execute(
                "INSERT INTO records (worker, seq) VALUES (%s, %s)",
                (worker_id, i),
            )


def run_postgres() -> str:
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS records")
        conn.execute(
            """
            CREATE TABLE records (
                id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                worker int NOT NULL,
                seq    int NOT NULL,
                UNIQUE (worker, seq)
            )
            """
        )
    procs = [Process(target=pg_worker, args=(w,)) for w in range(WORKERS)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    with psycopg.connect(DSN) as conn:
        count = conn.execute("SELECT count(*) FROM records").fetchone()[0]
    return f"{count} / {EXPECTED}"


def report(label: str, run) -> None:
    start = time.perf_counter()
    result = run()
    print(f"{label:<10} {result}  {time.perf_counter() - start:.1f}s", flush=True)


if __name__ == "__main__":
    report("JSON", run_json)
    report("Postgres", run_postgres)
