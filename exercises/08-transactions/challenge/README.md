# Challenge 08: Transactions and concurrency

Opcional.

## Enunciado

Folder: `exercises/08-transactions/challenge/`

**Goal.** Build a job queue in PostgreSQL that processes each job exactly once with several workers.

**Starting point.** An empty database (`./scripts/create-db.sh ch08 --reset`) with these tables:

```sql
CREATE TABLE job (
    job_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payload jsonb NOT NULL,
    status  text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done'))
);

CREATE TABLE job_result (
    job_id       bigint NOT NULL REFERENCES job,
    worker       integer NOT NULL,
    processed_at timestamptz NOT NULL DEFAULT now()
);
```

**Tasks.**

1. `producer.py` inserts 10,000 jobs with payload `{"n": <number>}`.
2. `worker.py` loops until there are no pending jobs. In one transaction it claims a job with `SELECT ... WHERE status = 'pending' ORDER BY job_id FOR UPDATE SKIP LOCKED LIMIT 1`, processes it (sleep 1 to 5 ms and insert a row into `job_result`), sets `status = 'done'` and commits.
3. Start 8 workers at the same time and prove that every job was processed exactly once: 10,000 rows in `job_result` and no `job_id` with more than one row.
4. Add one job whose processing sleeps 30 seconds. Kill the worker that takes it (`kill -9`) while it sleeps. Show what happens to the job, its row lock and its `job_result` row, and which worker processes it afterwards.

**Deliverables.**

- `producer.py`, `worker.py`, `pyproject.toml`.
- `README.md` with the commands, the queries that prove task 3, and the evidence and explanation of task 4, including what would change if processing sent an email instead of inserting a row.

**Done when.** Task 3 shows 10,000 results with no duplicates, and task 4 shows the killed job back in `pending` and later processed by another worker.
