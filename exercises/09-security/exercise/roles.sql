-- Exercise 09, task 1: least-privilege roles on ex09.
--
-- Run as postgres, with the three passwords in the environment (never in this file):
--   EX09_MIGRATIONS_PASSWORD=... EX09_APP_PASSWORD=... EX09_READONLY_PASSWORD=... \
--     psql -d ex09 -v ON_ERROR_STOP=1 -f exercises/09-security/exercise/roles.sql
--
-- Safe to run again: an existing role keeps its password.

\getenv migrations_password EX09_MIGRATIONS_PASSWORD
\getenv app_password EX09_APP_PASSWORD
\getenv readonly_password EX09_READONLY_PASSWORD

-- CREATE ROLE has no IF NOT EXISTS, and psql variables are not expanded inside a DO block,
-- so build each statement with format() (%I identifier, %L literal) and run it with \gexec.
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', r.name, r.password)
FROM (VALUES ('ex09_migrations', :'migrations_password'),
             ('ex09_app',        :'app_password'),
             ('ex09_readonly',   :'readonly_password')) AS r(name, password)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r.name)
\gexec

ALTER DATABASE ex09 OWNER TO ex09_migrations;

-- By default every role (PUBLIC) may create objects in public. Only migrations should.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
-- Pagila's public schema belongs to postgres, so owning the database is not enough:
-- migrations needs CREATE on the schema to add tables.
GRANT USAGE, CREATE ON SCHEMA public TO ex09_migrations;
GRANT USAGE ON SCHEMA public TO ex09_app, ex09_readonly;

-- The tables that exist now.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ex09_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO ex09_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ex09_readonly;

-- The tables that ex09_migrations creates later get the same grants without a new GRANT.
ALTER DEFAULT PRIVILEGES FOR ROLE ex09_migrations IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ex09_app;
ALTER DEFAULT PRIVILEGES FOR ROLE ex09_migrations IN SCHEMA public
    GRANT USAGE ON SEQUENCES TO ex09_app;
ALTER DEFAULT PRIVILEGES FOR ROLE ex09_migrations IN SCHEMA public
    GRANT SELECT ON TABLES TO ex09_readonly;
