-- Exercise 09, task 2: prove the privileges of roles.sql.
--
-- Run as postgres after roles.sql. Not with ON_ERROR_STOP: two statements must fail.
--   psql -d ex09 -e -f exercises/09-security/exercise/proofs.sql
--
-- Every change runs inside a transaction that is rolled back, so the file can run again.
-- A failed statement aborts its transaction, so each proof has its own.

-- 1. ex09_app may not drop tables.
BEGIN;
SET ROLE ex09_app;
SELECT current_user;
-- Expected: ERROR:  must be owner of table film
DROP TABLE film;
ROLLBACK;
RESET ROLE;

-- 2. ex09_app may insert (needs INSERT on actor and USAGE on actor_actor_id_seq).
BEGIN;
SET ROLE ex09_app;
SELECT current_user;
-- Expected: one row with the new actor_id (201 on a fresh copy of Pagila)
INSERT INTO actor (first_name, last_name) VALUES ('X', 'Y') RETURNING actor_id, first_name, last_name;
ROLLBACK;
RESET ROLE;

-- 3. ex09_readonly may read.
BEGIN;
SET ROLE ex09_readonly;
SELECT current_user;
-- Expected: count = 1000
SELECT count(*) FROM film;
ROLLBACK;
RESET ROLE;

-- 4. ex09_readonly may not write.
BEGIN;
SET ROLE ex09_readonly;
SELECT current_user;
-- Expected: ERROR:  permission denied for table actor
INSERT INTO actor (first_name, last_name) VALUES ('X', 'Y');
ROLLBACK;
RESET ROLE;

-- Back to postgres.
SELECT current_user;
