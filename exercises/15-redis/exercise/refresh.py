"""Refresh monthly_revenue under a Redis lock so only one process does it at a time.

Run two at once:  uv run python refresh.py & uv run python refresh.py & wait
"""

import os
import time
from datetime import datetime

from patterns import acquire_lock, pg_connect, r, release_lock

LOCK = "lock:refresh:monthly_revenue"
LOCK_TTL = 60
HOLD_SECONDS = 5


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S.%f}"[:-3] + f"] pid {os.getpid()}: {msg}", flush=True)


def main() -> None:
    token = acquire_lock(LOCK, LOCK_TTL)
    if token is None:
        log(f"skipped, lock {LOCK} is held (TTL {r.ttl(LOCK)} s)")
        return

    log(f"acquired {LOCK} (token {token[:8]}...)")
    try:
        with pg_connect() as conn:
            conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_revenue")
            months = conn.execute("SELECT count(*) FROM monthly_revenue").fetchone()[0]
        log(f"refreshed monthly_revenue ({months} months), holding the lock {HOLD_SECONDS} s")
        time.sleep(HOLD_SECONDS)
    finally:
        if release_lock(LOCK, token):
            log("released the lock")
        else:
            log("lock no longer ours (expired or taken), not deleted")


if __name__ == "__main__":
    main()
