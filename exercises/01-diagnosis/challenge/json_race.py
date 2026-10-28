"""10 processes append 1,000 records each to the same JSON file, without a lock.

Run from this folder:
    uv run json_race.py
"""

import json
import os
from multiprocessing import Process, Value
from pathlib import Path

WORKERS = 10
RECORDS_PER_WORKER = 1_000

JSON_FILE = Path(__file__).with_name("records.json")


def worker(worker_id: int, failed) -> None:
    for n in range(RECORDS_PER_WORKER):
        try:
            # Read the whole file, append one record, write the whole file back.
            records = json.loads(JSON_FILE.read_text())
            records.append({"worker": worker_id, "n": n})
            # Write to a temporary file and rename it over the original. Writing in
            # place truncates first, so two overlapping writes leave garbage at the
            # end and the file is never valid JSON again. The rename is atomic, but
            # it is not a lock: the read-modify-write cycle still races.
            tmp = JSON_FILE.with_name(f"{JSON_FILE.name}.{worker_id}.tmp")
            tmp.write_text(json.dumps(records))
            os.replace(tmp, JSON_FILE)
        except json.JSONDecodeError:
            # Another process was halfway through rewriting the file.
            with failed.get_lock():
                failed.value += 1


def main() -> None:
    JSON_FILE.write_text("[]")
    failed = Value("i", 0)
    procs = [Process(target=worker, args=(w, failed)) for w in range(WORKERS)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()

    try:
        count = len(json.loads(JSON_FILE.read_text()))
    except json.JSONDecodeError:
        count = "file is not valid JSON"
    print(f"records in file: {count} / {WORKERS * RECORDS_PER_WORKER}")
    print(f"failed writes:   {failed.value}")


if __name__ == "__main__":
    main()
