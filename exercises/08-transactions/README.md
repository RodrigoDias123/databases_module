# Exercício 08: Transactions and concurrency

## Enunciado

Folder: `exercises/08-transactions/exercise/`

**Goal.** Reproduce lost updates, deadlocks and write skew, and fix each one.

**Starting point.** A fresh copy of Pagila and a uv project:

```bash
./scripts/create-db.sh ex08 --pagila --reset
uv init --bare
uv add "psycopg[binary]"
```

Run this once in `ex08`. It adds a balance to every customer and brings store 1 from 6 to 20 active staff members:

```sql
ALTER TABLE customer ADD COLUMN balance numeric(10,2) NOT NULL DEFAULT 100 CHECK (balance >= 0);

INSERT INTO staff (first_name, last_name, address_id, store_id, username)
SELECT 'Temp', 'Staff ' || g, 1, 1, 'temp' || g
FROM generate_series(1, 14) AS g;
```

**Tasks.**

1. Lost update. In two `psql` sessions, each session withdraws 10 from customer 1 by reading the balance with `SELECT` and then writing the new value with `UPDATE ... SET balance = <value read - 10>`. Interleave the steps as in the tutorial so that the final balance is 90 instead of 80. Reset the balance to 100 afterwards.
2. Fix the lost update in two ways, repeating the same interleaving each time: an atomic `UPDATE ... SET balance = balance - 10 WHERE ... AND balance >= 10`, and `SELECT ... FOR UPDATE` before the update. Show that the final balance is 80 with both fixes.
3. Deadlock. In two sessions, session A updates customer 1 and then customer 2, and session B updates customer 2 and then customer 1, interleaved so that each waits for the other. Copy the full `ERROR: deadlock detected` message and explain each of its lines. Explain how to prevent it.
4. Write skew. The rule: every store keeps at least one active staff member. Write `write_skew.py`, which starts 20 threads, one per active staff member of store 1, each with its own connection. Each thread runs one transaction: count the active staff of store 1; if the count is above 1, set its own member to `active = false`; commit. Use a `threading.Barrier(20)` between the count and the update so that every thread reads before any thread writes.
   1. Run it under `READ COMMITTED` and show the number of active members of store 1 afterwards.
   2. Reset with `UPDATE staff SET active = true WHERE store_id = 1;`.
   3. Run it under `SERIALIZABLE`, retrying a transaction that fails with a serialisation error (SQLSTATE `40001`) from the start, without the barrier on retries. Show that exactly one member stays active.

**Deliverables.**

- `lost_update.md` and `deadlock.md` with the commands of each session in order (as a two-column table, like the tutorial) and the results.
- `write_skew.py`, `pyproject.toml`.
- `README.md` with the output of both runs of task 4 and an explanation of why `READ COMMITTED` breaks the rule and `SERIALIZABLE` does not.

**Done when.** The lost update and the deadlock are reproduced and explained, both fixes give a final balance of 80, the `READ COMMITTED` run leaves fewer than 1 active member, and the `SERIALIZABLE` run leaves exactly 1.

## Challenge (opcional, em `challenge/`)

Enunciado completo em [challenge/README.md](challenge/README.md).

## Checklist

- [ ] `lost_update.md`: lost update reproduced in two psql sessions (final balance 90)
- [ ] Fix 1: atomic `UPDATE` (final balance 80)
- [ ] Fix 2: `SELECT ... FOR UPDATE` (final balance 80)
- [ ] `deadlock.md`: deadlock reproduced, message explained line by line, prevention
- [ ] `write_skew.py`: rule broken under `READ COMMITTED`, exactly 1 active under `SERIALIZABLE` + retries
- [ ] `README.md` with the output of both runs and the explanation
