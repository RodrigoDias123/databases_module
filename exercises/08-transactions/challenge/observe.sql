-- State of the slow job, its row lock, its result and the backend that holds it.
-- Run with: psql -d ch08 -v job=<job_id> -f observe.sql
SELECT job_id, payload, status, xmax FROM job WHERE job_id = :job;

SELECT r.locked_row, r.locker, r.multi, r.modes, r.pids
FROM pgrowlocks('job') AS r;

SELECT count(*) AS results_for_job FROM job_result WHERE job_id = :job;

SELECT pid, state, backend_xid, now() - xact_start AS in_transaction_for, query
FROM pg_stat_activity
WHERE datname = 'ch08' AND application_name <> 'psql';

SELECT n_tup_ins, n_live_tup, n_dead_tup FROM pg_stat_user_tables WHERE relname = 'job_result';
