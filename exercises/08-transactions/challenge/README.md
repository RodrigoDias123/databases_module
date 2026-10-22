# Challenge 08: Transactions and concurrency

Obrigatório.

## Enunciado

Build a job queue in PostgreSQL: a `job` table, a producer that inserts 10,000 jobs, and 8 worker processes that claim jobs with `SELECT ... FOR UPDATE SKIP LOCKED LIMIT 1`, process them and mark them done. Prove that every job was processed exactly once. Then kill a worker halfway through a job and show what happens to that job.
