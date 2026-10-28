# Challenge 16: Redis II, source of truth, rebuild and persistence

Opcional.

## Enunciado

Folder: `exercises/16-consistency/challenge/`

**Goal.** Keep Redis in sync with PostgreSQL without a full rebuild, even when the worker or Redis fails, using the transactional outbox pattern.

**Starting point.** The `ex16` database, the sets built by `rebuild.py` and the `verify.py` of the exercise above. Turn on AOF with `docker-compose.redis-aof.yml` (following the warning in `sessions/16-redis-consistency/`), then run `CONFIG SET appendfsync always` in `redis-cli`. In this challenge, always restart Redis with the same `-f` files and run that `CONFIG SET` again after each restart, before the worker writes. Add this table to `ex16`:

```sql
CREATE TABLE outbox (
    outbox_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id  integer NOT NULL,
    film_id      integer NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    processed_at timestamptz
);
```

**Tasks.**

1. `rent.py` inserts N new rentals (the number is an argument) for random existing customers and copies. Each rental and its `outbox` row are inserted in the same PostgreSQL transaction.
2. `worker.py` loops: in one transaction it claims up to 50 unprocessed rows with `FOR UPDATE SKIP LOCKED`, adds the categories of each film to `customer:{customer_id}:categories`, sets `processed_at` and commits.
3. Run `rent.py 5000` while the worker runs. Kill the worker (`kill -9`) in the middle of a batch and start it again. Then stop Redis (`docker compose kill redis`) in the middle of a batch, start it again with AOF on and let the worker finish.
4. Run `verify.py` at the end.
5. Explain why processing the same outbox row twice is harmless here, and what you would need if it were not (for example an `INCR`). Explain also why the result depends on Redis persistence: what could be lost with RDB only, or with `appendfsync everysec`, and why the outbox alone would not bring it back.

**Deliverables.**

- `rent.py`, `worker.py`.
- `README.md` with the steps you ran, the worker log around both failures, the final output of `verify.py`, and the explanation of task 5.

**Done when.** After both failures, every outbox row is processed and `verify.py` exits with 0 without running `rebuild.py`.
