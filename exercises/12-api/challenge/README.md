# Challenge 12: ORM II, migrations, transactions and API

Opcional.

## Enunciado

Rename a column used by the API with zero downtime, using the expand and contract pattern across three migrations: (1) add the new column and keep both in sync with a trigger, (2) switch the code to the new column and backfill, (3) drop the old column and the trigger. Show that at every step both the old and the new version of the API work against the database.
