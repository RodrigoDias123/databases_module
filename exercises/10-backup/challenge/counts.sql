-- Row count of every table and partitioned table in public, one per line:
-- <table name><tab><rows>. Used by backup.sh (inside the dump's snapshot) and by
-- verify.sh (on the restored copy), so both sides count the same way.
SELECT c.relname,
       (xpath('/row/n/text()',
              query_to_xml(format('SELECT count(*) AS n FROM %I.%I', n.nspname, c.relname),
                           false, true, '')))[1]::text
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind IN ('r', 'p')
ORDER BY c.relname;
