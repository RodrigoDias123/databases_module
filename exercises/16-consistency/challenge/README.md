# Challenge 16: Redis II, source of truth, rebuild and persistence

Opcional.

## Enunciado

Implement the transactional outbox pattern: in the same PostgreSQL transaction as each new rental, insert a row into an `outbox` table. A separate worker reads unprocessed outbox rows (`FOR UPDATE SKIP LOCKED`), adds the film's category to `customer:{id}:categories` and marks the row processed. Kill the worker mid-batch and kill Redis mid-batch, restart both, and show with your verification script that Redis ends up correct without a full rebuild.
