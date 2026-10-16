# Exercício 08: Transactions and concurrency

## Enunciado

Folder: `exercises/08-transactions/`

1. Reproduce a lost update in two `psql` sessions (add a `balance` column to `customer` for this) and document the sequence of commands.
2. Fix it in two ways: atomic `UPDATE` and `SELECT ... FOR UPDATE`.
3. Cause a deadlock and explain the PostgreSQL message.
4. Write skew. Rule: every store keeps at least one active staff member. Add staff so that store 1 has 20 active members. A Python script sends 20 simultaneous requests, each deactivating a different member after checking the count of active staff. Show the rule broken under `READ COMMITTED`, then fix it with `SERIALIZABLE` and retries, and prove that exactly one member stays active.

Marked 2 when all four points are done and the script proves the result.

Group project: the critical transactions of your scenario in SQL, and the first version of the concurrency test in `tests/concurrency/`.

## Challenge (opcional, em `challenge/`)

Build a job queue in PostgreSQL: a `job` table, a producer that inserts 10,000 jobs, and 8 worker processes that claim jobs with `SELECT ... FOR UPDATE SKIP LOCKED LIMIT 1`, process them and mark them done. Prove that every job was processed exactly once. Then kill a worker halfway through a job and show what happens to that job.

## Checklist

- [ ] Lost update reproduced in two psql sessions (balance column on customer), with command sequence
- [ ] Fix 1: atomic UPDATE
- [ ] Fix 2: SELECT ... FOR UPDATE
- [ ] Deadlock caused and PostgreSQL message explained
- [ ] Write skew: Python script with 20 simultaneous requests, rule broken under READ COMMITTED, fixed with SERIALIZABLE + retries, exactly one member stays active
